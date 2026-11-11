"""Persistencia de evaluaciones en SQLite (local) o PostgreSQL (producción).

Si DATABASE_URL contiene una URL PostgreSQL, se utiliza Neon mediante asyncpg.
Si no existe DATABASE_URL, se conserva SQLite usando SQLITE_DB_PATH.
"""

import asyncio
import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

DB_PATH = os.getenv("SQLITE_DB_PATH", "evaluaciones.db")
logger = logging.getLogger("backend_app")

_pg_pool = None


class DatabaseConfigurationError(RuntimeError):
    """La configuración de la base de datos no es válida."""


def _database_url() -> str | None:
    value = os.getenv("DATABASE_URL", "").strip()
    return value or None


def backend_activo() -> str:
    """Devuelve el motor seleccionado y rechaza URLs no compatibles."""
    url = _database_url()
    if not url:
        return "sqlite"
    if url.startswith(("postgres://", "postgresql://")):
        return "postgresql"
    raise DatabaseConfigurationError(
        "DATABASE_URL debe comenzar con postgres:// o postgresql://."
    )


def _parametros_postgres() -> dict:
    """Convierte la URL de Neon en argumentos compatibles con asyncpg.

    Neon entrega parámetros libpq como sslmode y channel_binding. asyncpg
    recibe TLS mediante ssl=True y negocia SCRAM/channel binding directamente.
    """
    raw_url = _database_url()
    if not raw_url:
        raise DatabaseConfigurationError("DATABASE_URL no está configurada.")

    parsed = urlsplit(raw_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise DatabaseConfigurationError(
            "DATABASE_URL debe comenzar con postgres:// o postgresql://."
        )
    if not parsed.hostname or not parsed.path.strip("/"):
        raise DatabaseConfigurationError(
            "DATABASE_URL debe incluir el servidor y el nombre de la base de datos."
        )

    query = parse_qs(parsed.query)
    sslmode = query.get("sslmode", ["require"])[0].lower()

    return {
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": unquote(parsed.path.lstrip("/")),
        # Neon requiere TLS. ssl=True usa la validación TLS predeterminada.
        "ssl": sslmode != "disable",
        # Evita depender de prepared statements con proxies de pooling.
        "statement_cache_size": 0,
        "command_timeout": 30,
    }


async def _configurar_conexion_postgres(conn):
    """Hace que asyncpg convierta JSON/JSONB automáticamente a objetos Python."""
    await conn.set_type_codec(
        "json",
        schema="pg_catalog",
        encoder=lambda valor: json.dumps(valor, ensure_ascii=False),
        decoder=json.loads,
        format="text",
    )
    await conn.set_type_codec(
        "jsonb",
        schema="pg_catalog",
        encoder=lambda valor: json.dumps(valor, ensure_ascii=False),
        decoder=json.loads,
        format="text",
    )


async def _obtener_pool_postgres():
    global _pg_pool
    if _pg_pool is None:
        try:
            import asyncpg
        except ImportError as exc:
            raise RuntimeError(
                "Falta asyncpg. Instala las dependencias de backend/requirements.txt."
            ) from exc

        _pg_pool = await asyncpg.create_pool(
            **_parametros_postgres(),
            min_size=1,
            max_size=5,
            init=_configurar_conexion_postgres,
        )
        logger.info("[BD] Pool PostgreSQL inicializado.")
    return _pg_pool


def _conexion_sqlite():
    ruta = Path(DB_PATH)
    if str(DB_PATH) != ":memory:":
        ruta.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH), timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


@contextmanager
def _sqlite_db():
    db = _conexion_sqlite()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _inicializar_sqlite():
    with _sqlite_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS tareas (
                id TEXT PRIMARY KEY,
                estado TEXT NOT NULL,
                tiempo_ejecucion_seg REAL,
                resultado JSON,
                mensaje TEXT,
                fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                url TEXT
            )
            """
        )
        columnas = {
            fila[1] for fila in db.execute("PRAGMA table_info(tareas)").fetchall()
        }
        if "url" not in columnas:
            db.execute("ALTER TABLE tareas ADD COLUMN url TEXT")
        db.commit()


def _fecha_a_epoch_ms(valor) -> int | None:
    if valor is None:
        return None
    if isinstance(valor, str):
        try:
            valor = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(valor, datetime):
        return None
    if valor.tzinfo is None:
        # CURRENT_TIMESTAMP de SQLite se almacena en UTC sin sufijo de zona.
        valor = valor.replace(tzinfo=timezone.utc)
    return int(valor.timestamp() * 1000)


def _normalizar_tarea(fila) -> dict | None:
    if fila is None:
        return None
    tarea = dict(fila)
    resultado = tarea.get("resultado")
    if isinstance(resultado, str):
        try:
            resultado = json.loads(resultado)
        except (TypeError, json.JSONDecodeError):
            resultado = None

    fecha_creacion = tarea.get("fecha_creacion")
    respuesta = {
        "id": tarea["id"],
        "estado": tarea["estado"],
        "fecha": _fecha_a_epoch_ms(fecha_creacion),
    }
    if tarea.get("url") is not None:
        respuesta["url"] = tarea["url"]
    if tarea.get("tiempo_ejecucion_seg") is not None:
        respuesta["tiempo_ejecucion_seg"] = tarea["tiempo_ejecucion_seg"]
    if resultado is not None:
        respuesta["resultado"] = resultado
    if tarea.get("mensaje"):
        respuesta["mensaje"] = tarea["mensaje"]
    return respuesta


async def init_db():
    """Crea la tabla y aplica la migración compatible de la columna URL."""
    if backend_activo() == "postgresql":
        pool = await _obtener_pool_postgres()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tareas (
                    id TEXT PRIMARY KEY,
                    estado TEXT NOT NULL,
                    tiempo_ejecucion_seg DOUBLE PRECISION,
                    resultado JSONB,
                    mensaje TEXT,
                    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    url TEXT
                )
                """
            )
            await conn.execute(
                "ALTER TABLE tareas ADD COLUMN IF NOT EXISTS url TEXT"
            )
        logger.info("[BD] Tabla 'tareas' inicializada en PostgreSQL.")
        return

    await asyncio.to_thread(_inicializar_sqlite)
    logger.info("[BD] Tabla 'tareas' inicializada en SQLite.")


async def close_db():
    """Cierra el pool PostgreSQL al apagar FastAPI."""
    global _pg_pool
    if _pg_pool is not None:
        await _pg_pool.close()
        _pg_pool = None


async def guardar_tarea_inicial(
    tarea_id: str,
    estado: str = "en_proceso",
    url: str | None = None,
):
    """Registra la tarea al momento del POST /analizar."""
    if backend_activo() == "postgresql":
        pool = await _obtener_pool_postgres()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO tareas (id, estado, url) VALUES ($1, $2, $3)",
                tarea_id,
                estado,
                url,
            )
        return

    def guardar():
        with _sqlite_db() as db:
            db.execute(
                "INSERT INTO tareas (id, estado, url) VALUES (?, ?, ?)",
                (tarea_id, estado, url),
            )
            db.commit()

    await asyncio.to_thread(guardar)


async def guardar_tarea_resultado(
    tarea_id: str,
    estado: str,
    duracion: float,
    resultado: dict | None = None,
    mensaje: str | None = None,
):
    """Actualiza el estado y el resultado de una evaluación."""
    duracion_redondeada = round(duracion, 4)
    if backend_activo() == "postgresql":
        pool = await _obtener_pool_postgres()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE tareas
                SET estado = $1, tiempo_ejecucion_seg = $2,
                    resultado = $3, mensaje = $4
                WHERE id = $5
                """,
                estado,
                duracion_redondeada,
                resultado,
                mensaje,
                tarea_id,
            )
        return

    resultado_json = (
        json.dumps(resultado, ensure_ascii=False) if resultado is not None else None
    )

    def guardar():
        with _sqlite_db() as db:
            db.execute(
                """
                UPDATE tareas
                SET estado = ?, tiempo_ejecucion_seg = ?, resultado = ?, mensaje = ?
                WHERE id = ?
                """,
                (estado, duracion_redondeada, resultado_json, mensaje, tarea_id),
            )
            db.commit()

    await asyncio.to_thread(guardar)


async def obtener_tarea_por_id(tarea_id: str) -> dict | None:
    """Devuelve una evaluación por ID, incluyendo el reporte completo."""
    if backend_activo() == "postgresql":
        pool = await _obtener_pool_postgres()
        async with pool.acquire() as conn:
            fila = await conn.fetchrow(
                """
                SELECT id, estado, tiempo_ejecucion_seg, resultado, mensaje,
                       fecha_creacion, url
                FROM tareas WHERE id = $1
                """,
                tarea_id,
            )
        return _normalizar_tarea(fila)

    def consultar():
        with _sqlite_db() as db:
            return db.execute(
                """
                SELECT id, estado, tiempo_ejecucion_seg, resultado, mensaje,
                       fecha_creacion, url
                FROM tareas WHERE id = ?
                """,
                (tarea_id,),
            ).fetchone()

    fila = await asyncio.to_thread(consultar)
    return _normalizar_tarea(fila)


async def listar_tareas(limit: int = 50, offset: int = 0) -> dict:
    """Lista evaluaciones compartidas, de más recientes a más antiguas."""
    limite = max(1, min(int(limit), 100))
    desplazamiento = max(0, int(offset))

    if backend_activo() == "postgresql":
        pool = await _obtener_pool_postgres()
        async with pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM tareas")
            filas = await conn.fetch(
                """
                SELECT id, estado, tiempo_ejecucion_seg, resultado, mensaje,
                       fecha_creacion, url
                FROM tareas
                ORDER BY fecha_creacion DESC, id DESC
                LIMIT $1 OFFSET $2
                """,
                limite,
                desplazamiento,
            )
        items = [_normalizar_tarea(fila) for fila in filas]
    else:
        def consultar():
            with _sqlite_db() as db:
                total = db.execute("SELECT COUNT(*) FROM tareas").fetchone()[0]
                filas = db.execute(
                    """
                    SELECT id, estado, tiempo_ejecucion_seg, resultado, mensaje,
                           fecha_creacion, url
                    FROM tareas
                    ORDER BY fecha_creacion DESC, id DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limite, desplazamiento),
                ).fetchall()
                return total, filas

        total, filas = await asyncio.to_thread(consultar)
        items = [_normalizar_tarea(fila) for fila in filas]

    return {
        "items": items,
        "total": int(total or 0),
        "limit": limite,
        "offset": desplazamiento,
    }


async def importar_tarea(tarea: dict) -> bool:
    """Importa una evaluación legada sin sobrescribir un ID ya existente.

    Se utiliza únicamente para migrar un archivo SQLite anterior a Neon.
    Devuelve True si se insertó la evaluación y False si ya existía.
    """
    fecha = tarea.get("fecha_creacion")
    if isinstance(fecha, str):
        try:
            fecha = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
        except ValueError:
            fecha = None
    if isinstance(fecha, datetime) and fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)

    resultado = tarea.get("resultado")
    if isinstance(resultado, str):
        try:
            resultado = json.loads(resultado)
        except json.JSONDecodeError:
            resultado = None

    valores = (
        tarea["id"],
        tarea.get("estado", "error"),
        tarea.get("tiempo_ejecucion_seg"),
        resultado,
        tarea.get("mensaje"),
        fecha,
        tarea.get("url"),
    )

    if backend_activo() == "postgresql":
        pool = await _obtener_pool_postgres()
        async with pool.acquire() as conn:
            estado = await conn.execute(
                """
                INSERT INTO tareas
                    (id, estado, tiempo_ejecucion_seg, resultado, mensaje, fecha_creacion, url)
                VALUES ($1, $2, $3, $4, $5, COALESCE($6::timestamptz, CURRENT_TIMESTAMP), $7)
                ON CONFLICT (id) DO NOTHING
                """,
                *valores,
            )
        return estado.endswith(" 1")

    def importar():
        with _sqlite_db() as db:
            cursor = db.execute(
                """
                INSERT OR IGNORE INTO tareas
                    (id, estado, tiempo_ejecucion_seg, resultado, mensaje, fecha_creacion, url)
                VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP), ?)
                """,
                (
                    valores[0], valores[1], valores[2],
                    json.dumps(resultado, ensure_ascii=False) if resultado is not None else None,
                    valores[4],
                    fecha.isoformat(sep=" ") if isinstance(fecha, datetime) else fecha,
                    valores[6],
                ),
            )
            db.commit()
            return cursor.rowcount == 1

    return await asyncio.to_thread(importar)


async def eliminar_tareas_antiguas(horas: int = 24) -> int:
    """Elimina tareas antiguas. No se ejecuta automáticamente por defecto."""
    horas = max(1, int(horas))
    if backend_activo() == "postgresql":
        pool = await _obtener_pool_postgres()
        async with pool.acquire() as conn:
            estado = await conn.execute(
                "DELETE FROM tareas WHERE fecha_creacion < NOW() - ($1 * INTERVAL '1 hour')",
                horas,
            )
        return int(estado.rsplit(" ", 1)[-1])

    def eliminar():
        with _sqlite_db() as db:
            cursor = db.execute(
                "DELETE FROM tareas WHERE fecha_creacion < datetime('now', ?)",
                (f"-{horas} hours",),
            )
            db.commit()
            return cursor.rowcount

    return await asyncio.to_thread(eliminar)
