import asyncio
import sqlite3
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from app.db import database, limpieza


@pytest.fixture
def ruta_db(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    ruta = str(tmp_path / "persistencia_prueba.db")
    monkeypatch.setattr(database, "DB_PATH", ruta)
    return ruta


def test_resultado_persiste_al_cerrar_y_reabrir_la_base(ruta_db):
    async def escenario():
        await database.init_db()
        await database.guardar_tarea_inicial("persistente", url="https://example.org")
        await database.guardar_tarea_resultado(
            "persistente", "completado", 1.23456,
            {"texto": "Evaluación válida"},
        )
        tarea = await database.obtener_tarea_por_id("persistente")
        assert tarea["id"] == "persistente"
        assert tarea["estado"] == "completado"
        assert tarea["tiempo_ejecucion_seg"] == 1.2346
        assert tarea["resultado"] == {"texto": "Evaluación válida"}
        assert tarea["url"] == "https://example.org"
        assert tarea["fecha"] is not None
        assert await database.obtener_tarea_por_id("no-existe") is None

    asyncio.run(escenario())


def test_historial_compartido_se_ordena_y_pagina(ruta_db):
    async def escenario():
        await database.init_db()
        for identificador in ("primera", "segunda", "tercera"):
            await database.guardar_tarea_inicial(identificador, url=f"https://{identificador}.example")
        pagina = await database.listar_tareas(limit=2, offset=0)
        siguiente = await database.listar_tareas(limit=2, offset=2)
        assert pagina["total"] == 3
        assert len(pagina["items"]) == 2
        assert len(siguiente["items"]) == 1
        assert {tarea["id"] for tarea in pagina["items"] + siguiente["items"]} == {
            "primera", "segunda", "tercera"
        }

    asyncio.run(escenario())


def test_limpieza_manual_purga_solo_registros_mayores_a_24_horas(ruta_db):
    async def escenario():
        await database.init_db()
        await database.guardar_tarea_inicial("reciente")
        await database.guardar_tarea_inicial("expirada")
        db = sqlite3.connect(ruta_db)
        try:
            db.execute(
                "UPDATE tareas SET fecha_creacion = datetime('now', '-25 hours') WHERE id = ?",
                ("expirada",),
            )
            db.commit()
        finally:
            db.close()
        eliminadas = await database.eliminar_tareas_antiguas(24)
        assert eliminadas == 1
        assert await database.obtener_tarea_por_id("reciente") is not None
        assert await database.obtener_tarea_por_id("expirada") is None

    asyncio.run(escenario())


def test_limpieza_se_puede_cancelar(monkeypatch):
    async def cancelar(_horas):
        raise asyncio.CancelledError

    monkeypatch.setattr(limpieza, "eliminar_tareas_antiguas", cancelar)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(limpieza.tarea_limpieza_24h())


def test_limpieza_registra_un_fallo_y_espera_el_siguiente_ciclo(monkeypatch):
    async def detener(_):
        raise asyncio.CancelledError

    monkeypatch.setattr(limpieza.asyncio, "sleep", detener)
    monkeypatch.setattr(
        limpieza,
        "eliminar_tareas_antiguas",
        Mock(side_effect=RuntimeError("base no disponible")),
    )
    registrar = Mock()
    monkeypatch.setattr(limpieza.logger, "error", registrar)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(limpieza.tarea_limpieza_24h())
    assert "base no disponible" in str(registrar.call_args.args[1])


def test_migracion_anade_la_url_y_respeta_reportes_existentes(ruta_db):
    db = sqlite3.connect(ruta_db)
    try:
        db.execute(
            """CREATE TABLE tareas (
                id TEXT PRIMARY KEY, estado TEXT NOT NULL,
                tiempo_ejecucion_seg REAL, resultado JSON, mensaje TEXT,
                fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        db.execute(
            "INSERT INTO tareas (id, estado, resultado) VALUES (?, ?, ?)",
            ("legado", "completado", '{"texto":"anterior"}'),
        )
        db.commit()
    finally:
        db.close()

    async def verificar():
        await database.init_db()
        await database.init_db()
        assert (await database.obtener_tarea_por_id("legado"))["resultado"]["texto"] == "anterior"
        await database.guardar_tarea_inicial("nuevo", url="https://example.org")
        assert (await database.obtener_tarea_por_id("nuevo"))["url"] == "https://example.org"

    asyncio.run(verificar())


def test_importacion_de_sqlite_conserva_id_fecha_y_reporte(ruta_db):
    async def escenario():
        await database.init_db()
        fecha = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        insertado = await database.importar_tarea({
            "id": "reporte-legado",
            "estado": "completado",
            "url": "https://example.org",
            "tiempo_ejecucion_seg": 2.5,
            "resultado": {"riesgo": {"puntuacion": 1}},
            "fecha_creacion": fecha,
        })
        duplicado = await database.importar_tarea({"id": "reporte-legado", "estado": "error"})
        tarea = await database.obtener_tarea_por_id("reporte-legado")
        assert insertado is True
        assert duplicado is False
        assert tarea["resultado"] == {"riesgo": {"puntuacion": 1}}
        assert tarea["fecha"] == int(fecha.timestamp() * 1000)

    asyncio.run(escenario())


def test_parsea_url_de_neon_sin_revelar_credenciales(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://usuario:clave%40privada@ep-ejemplo-pooler.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
    )
    parametros = database._parametros_postgres()
    assert parametros["user"] == "usuario"
    assert parametros["password"] == "clave@privada"
    assert parametros["host"] == "ep-ejemplo-pooler.aws.neon.tech"
    assert parametros["database"] == "neondb"
    assert parametros["ssl"] is True
    assert parametros["statement_cache_size"] == 0


def test_rechaza_una_database_url_con_motor_no_soportado(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql://usuario:clave@servidor/base")
    with pytest.raises(database.DatabaseConfigurationError):
        database.backend_activo()


def test_ruta_postgres_usa_pool_tls_json_y_operaciones_compartidas(monkeypatch):
    import sys
    from datetime import datetime, timezone
    from types import SimpleNamespace

    fila = {
        "id": "pg-1",
        "estado": "completado",
        "tiempo_ejecucion_seg": 1.5,
        "resultado": {"riesgo": {"puntuacion": 2}},
        "mensaje": None,
        "fecha_creacion": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "url": "https://example.org",
    }

    class ConexionFalsa:
        def __init__(self):
            self.codecs = []
            self.consultas = []

        async def set_type_codec(self, *args, **kwargs):
            self.codecs.append((args, kwargs))

        async def execute(self, consulta, *args):
            self.consultas.append((consulta, args))
            if consulta.lstrip().startswith("INSERT"):
                return "INSERT 0 1"
            if consulta.lstrip().startswith("DELETE"):
                return "DELETE 1"
            return "OK"

        async def fetchrow(self, consulta, *args):
            self.consultas.append((consulta, args))
            return fila

        async def fetchval(self, consulta, *args):
            self.consultas.append((consulta, args))
            return 1

        async def fetch(self, consulta, *args):
            self.consultas.append((consulta, args))
            return [fila]

    class Adquirir:
        def __init__(self, conexion):
            self.conexion = conexion

        async def __aenter__(self):
            return self.conexion

        async def __aexit__(self, *_):
            return False

    class PoolFalso:
        def __init__(self, conexion):
            self.conexion = conexion
            self.cerrado = False

        def acquire(self):
            return Adquirir(self.conexion)

        async def close(self):
            self.cerrado = True

    conexion = ConexionFalsa()
    pool = PoolFalso(conexion)
    argumentos_pool = {}

    async def crear_pool(**kwargs):
        argumentos_pool.update(kwargs)
        await kwargs["init"](conexion)
        return pool

    monkeypatch.setattr(database, "_pg_pool", None)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://usuario:clave@ep-ejemplo-pooler.neon.tech/neondb?sslmode=require&channel_binding=require",
    )
    monkeypatch.setitem(sys.modules, "asyncpg", SimpleNamespace(create_pool=crear_pool))

    async def escenario():
        await database.init_db()
        assert argumentos_pool["ssl"] is True
        assert argumentos_pool["statement_cache_size"] == 0
        assert argumentos_pool["max_size"] == 5
        assert len(conexion.codecs) == 2

        await database.guardar_tarea_inicial("pg-nueva", url="https://nueva.example")
        await database.guardar_tarea_resultado(
            "pg-nueva", "completado", 1.5, {"ok": True}
        )
        tarea = await database.obtener_tarea_por_id("pg-1")
        pagina = await database.listar_tareas(limit=10, offset=0)
        assert tarea["resultado"] == fila["resultado"]
        assert tarea["fecha"] == int(fila["fecha_creacion"].timestamp() * 1000)
        assert pagina["total"] == 1
        assert pagina["items"][0]["id"] == "pg-1"
        assert await database.importar_tarea({"id": "importada", "estado": "completado"})
        assert await database.eliminar_tareas_antiguas(24) == 1
        await database.close_db()
        assert pool.cerrado is True

    asyncio.run(escenario())


def _modulo_migracion():
    import importlib.util
    from pathlib import Path

    ruta = Path(__file__).resolve().parents[1] / "backend" / "scripts" / "migrar_sqlite_a_neon.py"
    spec = importlib.util.spec_from_file_location("migrar_sqlite_a_neon_test", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_script_migracion_lee_sqlite_legado_sin_columna_url(tmp_path):
    ruta = tmp_path / "legado.db"
    db = sqlite3.connect(ruta)
    try:
        db.execute(
            """CREATE TABLE tareas (
                id TEXT PRIMARY KEY, estado TEXT NOT NULL,
                tiempo_ejecucion_seg REAL, resultado JSON, mensaje TEXT,
                fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        db.execute(
            "INSERT INTO tareas (id, estado, resultado) VALUES (?, ?, ?)",
            ("legado", "completado", '{"ok":true}'),
        )
        db.commit()
    finally:
        db.close()

    registros = _modulo_migracion().leer_sqlite(ruta)
    assert len(registros) == 1
    assert registros[0]["id"] == "legado"
    assert registros[0]["url"] is None


def test_script_migracion_informa_archivo_o_tabla_ausente(tmp_path):
    modulo = _modulo_migracion()
    with pytest.raises(FileNotFoundError):
        modulo.leer_sqlite(tmp_path / "no-existe.db")

    ruta = tmp_path / "sin_tabla.db"
    sqlite3.connect(ruta).close()
    with pytest.raises(RuntimeError, match="no contiene la tabla tareas"):
        modulo.leer_sqlite(ruta)


def test_script_migracion_exige_postgresql(monkeypatch, tmp_path):
    modulo = _modulo_migracion()
    monkeypatch.setattr(modulo, "backend_activo", lambda: "sqlite")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        asyncio.run(modulo.ejecutar(tmp_path / "no-se-lee.db"))


def test_script_migracion_importa_sin_duplicar_y_cierra_pool(monkeypatch, tmp_path, capsys):
    from unittest.mock import AsyncMock

    modulo = _modulo_migracion()
    monkeypatch.setattr(modulo, "backend_activo", lambda: "postgresql")
    monkeypatch.setattr(modulo, "leer_sqlite", Mock(return_value=[{"id": "a"}, {"id": "b"}]))
    inicializar = AsyncMock()
    importar = AsyncMock(side_effect=[True, False])
    cerrar = AsyncMock()
    monkeypatch.setattr(modulo, "init_db", inicializar)
    monkeypatch.setattr(modulo, "importar_tarea", importar)
    monkeypatch.setattr(modulo, "close_db", cerrar)

    asyncio.run(modulo.ejecutar(tmp_path / "origen.db"))

    inicializar.assert_awaited_once()
    assert importar.await_count == 2
    cerrar.assert_awaited_once()
    salida = capsys.readouterr().out
    assert "Registros leídos desde SQLite: 2" in salida
    assert "Registros importados a Neon: 1" in salida
    assert "Registros omitidos por ID ya existente: 1" in salida


def test_script_migracion_main_acepta_ruta_de_origen(monkeypatch, tmp_path):
    from unittest.mock import AsyncMock
    import sys

    modulo = _modulo_migracion()
    ruta = tmp_path / "origen.db"
    async def ejecutar_falso(origen):
        return origen

    ejecutar = Mock(side_effect=ejecutar_falso)
    correr = Mock(side_effect=lambda coroutine: coroutine.close())
    monkeypatch.setattr(modulo, "ejecutar", ejecutar)
    monkeypatch.setattr(modulo.asyncio, "run", correr)
    monkeypatch.setattr(sys, "argv", ["migrar_sqlite_a_neon.py", "--source", str(ruta)])

    modulo.main()

    correr.assert_called_once()
    ejecutar.assert_called_once_with(ruta.resolve())


@pytest.mark.parametrize("eliminadas", [0, 2])
def test_limpieza_registra_cantidad_solo_si_hubo_purgas(monkeypatch, eliminadas):
    async def eliminar(_horas):
        return eliminadas

    async def detener(_):
        raise asyncio.CancelledError

    monkeypatch.setattr(limpieza, "eliminar_tareas_antiguas", eliminar)
    monkeypatch.setattr(limpieza.asyncio, "sleep", detener)
    registrar = Mock()
    monkeypatch.setattr(limpieza.logger, "info", registrar)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(limpieza.tarea_limpieza_24h())

    assert registrar.called is (eliminadas > 0)
