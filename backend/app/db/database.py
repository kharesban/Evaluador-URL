# app/db/database.py
import json
import logging
import aiosqlite

DB_PATH = "evaluaciones.db"
logger = logging.getLogger("backend_app")

async def init_db():
    """Crea la tabla de tareas/evaluaciones en SQLite si no existe."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tareas (
                id TEXT PRIMARY KEY,
                estado TEXT NOT NULL,
                tiempo_ejecucion_seg REAL,
                resultado JSON,
                mensaje TEXT,
                fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
        logger.info("[BD] Tabla 'tareas' inicializada en SQLite (evaluaciones.db).")

async def guardar_tarea_inicial(tarea_id: str, estado: str = "en_proceso"):
    """Registra la tarea al momento del POST /analizar."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO tareas (id, estado) VALUES (?, ?)",
            (tarea_id, estado)
        )
        await db.commit()

async def guardar_tarea_resultado(tarea_id: str, estado: str, duracion: float, resultado: dict = None, mensaje: str = None):
    """Guarda el resultado devuelto por worker.py cuando finaliza la evaluación."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE tareas 
            SET estado = ?, tiempo_ejecucion_seg = ?, resultado = ?, mensaje = ?
            WHERE id = ?
            """,
            (
                estado,
                round(duracion, 4),
                json.dumps(resultado, ensure_ascii=False) if resultado else None,
                mensaje,
                tarea_id
            )
        )
        await db.commit()

async def obtener_tarea_por_id(tarea_id: str) -> dict | None:
    """Devuelve los datos al frontend durante las peticiones de Polling (GET /tareas/{tarea_id})."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, estado, tiempo_ejecucion_seg, resultado, mensaje FROM tareas WHERE id = ?",
            (tarea_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            
            res_dict = {
                "id": row["id"],
                "estado": row["estado"],
            }
            if row["tiempo_ejecucion_seg"] is not None:
                res_dict["tiempo_ejecucion_seg"] = row["tiempo_ejecucion_seg"]
            if row["resultado"]:
                res_dict["resultado"] = json.loads(row["resultado"])
            if row["mensaje"]:
                res_dict["mensaje"] = row["mensaje"]
                
            return res_dict