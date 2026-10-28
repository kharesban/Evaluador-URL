# app/db/limpieza.py
import asyncio
import logging
import aiosqlite

DB_PATH = "evaluaciones.db"
logger = logging.getLogger("backend_app")

async def tarea_limpieza_24h(intervalo_segundos: int = 3600):
    """Se ejecuta en segundo plano y elimina los registros con más de 24 horas de antigüedad."""
    while True:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute("""
                    DELETE FROM tareas 
                    WHERE fecha_creacion < datetime('now', '-24 hours')
                """)
                await db.commit()
                if cursor.rowcount > 0:
                    logger.info(f"[BD LIMPIEZA] Purgadas {cursor.rowcount} evaluaciones con antigüedad mayor a 24h.")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[BD LIMPIEZA ERROR] Fallo durante la purga: {e}")
            
        await asyncio.sleep(intervalo_segundos)