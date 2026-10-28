import asyncio
import logging
import sys
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv

ruta_env = Path(__file__).resolve().parent / ".env"
load_dotenv(ruta_env, override=True)

# Importación de la Base de Datos SQLite y Limpieza
from app.db.database import (
    init_db,
    guardar_tarea_inicial,
    guardar_tarea_resultado,
    obtener_tarea_por_id
)
from app.db.limpieza import tarea_limpieza_24h

# ==========================================
# 1. CONFIGURACIÓN DE LOGS EN MEMORIA Y CONSOLA
# ==========================================
LOG_BUFFER = deque(maxlen=200)

class InMemoryLogHandler(logging.Handler):
    """Handler personalizado para guardar los registros de log en memoria para /logs."""
    def emit(self, record):
        msg = self.format(record)
        LOG_BUFFER.append(msg)

formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

memory_handler = InMemoryLogHandler()
memory_handler.setFormatter(formatter)

logger = logging.getLogger("backend_app")
logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)
logger.addHandler(memory_handler)

# ==========================================
# 2. CONFIGURACIÓN DE RUTAS Y MÓDULOS
# ==========================================
carpeta_worker = Path(__file__).resolve().parent / "app" / "evaluador-worker"
sys.path.insert(0, str(carpeta_worker))

from worker import procesar_analisis

# Ciclo de vida asíncrono Lifespan para la BD y tarea de purga a 24 horas
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Al arrancar el servidor
    await init_db()
    limpieza_task = asyncio.create_task(tarea_limpieza_24h(intervalo_segundos=3600))
    
    yield
    
    # Al detener el servidor
    limpieza_task.cancel()

app = FastAPI(title="Evaluador de URL", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

class SolicitudAnalisis(BaseModel):
    url: HttpUrl

# ==========================================
# 3. PROCESAMIENTO CON MEDICIÓN DE TIEMPOS
# ==========================================
async def ejecutar_analisis(tarea_id: str, url: str):
    logger.info(f"[TAREA {tarea_id}] Iniciando análisis asíncrono para: {url}")
    t_inicio = time.perf_counter()

    try:
        resultado = await procesar_analisis(url)
        duracion = time.perf_counter() - t_inicio
        
        logger.debug(f"[PERFORMANCE] Tarea {tarea_id} finalizada en {duracion:.4f}s")

        # Persistir resultado exitoso en SQLite
        await guardar_tarea_resultado(
            tarea_id=tarea_id,
            estado="completado",
            duracion=duracion,
            resultado=resultado
        )
    except Exception as e:
        duracion = time.perf_counter() - t_inicio
        logger.exception(f"[ERROR] Falló el análisis de la tarea {tarea_id} tras {duracion:.4f}s: {e}")

        # Persistir error en SQLite
        await guardar_tarea_resultado(
            tarea_id=tarea_id,
            estado="error",
            duracion=duracion,
            mensaje="No fue posible completar el análisis."
        )

# ==========================================
# 4. ENDPOINTS DE LA API
# ==========================================
@app.post("/analizar", status_code=202)
async def iniciar_analisis(
    solicitud: SolicitudAnalisis,
    background_tasks: BackgroundTasks,
):
    tarea_id = str(uuid4())
    logger.info(f"Petición recibida en /analizar. Asignado ID: {tarea_id}")

    # Guardar en SQLite con estado 'en_proceso'
    await guardar_tarea_inicial(tarea_id, estado="en_proceso")

    background_tasks.add_task(
        ejecutar_analisis,
        tarea_id,
        str(solicitud.url),
    )

    return {"id": tarea_id, "estado": "en_proceso"}

@app.get("/tareas/{tarea_id}")
async def consultar_tarea(tarea_id: str):
    # Consultar estado directamente en SQLite
    tarea = await obtener_tarea_por_id(tarea_id)

    if tarea is None:
        logger.warning(f"Consulta a tarea inexistente: {tarea_id}")
        raise HTTPException(
            status_code=404,
            detail="La tarea no existe o expiró tras 24 horas.",
        )

    return tarea

@app.get("/logs", tags=["Monitoreo"])
def obtener_logs():
    """Devuelve los últimos 200 registros de log generados por el servidor."""
    return {
        "total_registros": len(LOG_BUFFER),
        "logs": list(LOG_BUFFER)
    }