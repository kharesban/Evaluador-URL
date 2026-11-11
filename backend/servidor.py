import asyncio
import logging
import os
import sys
import time
from collections import deque
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

ruta_env = Path(__file__).resolve().parent / ".env"
load_dotenv(ruta_env, override=False)

# Importación de persistencia compartida y limpieza opcional
from app.db.database import (
    init_db,
    guardar_tarea_inicial,
    guardar_tarea_resultado,
    obtener_tarea_por_id,
    listar_tareas,
    close_db,
    backend_activo,
)
from app.db.limpieza import tarea_limpieza_24h

# ==========================================
# 1. CONFIGURACIÓN DE LOGS EN MEMORIA Y CONSOLA
# ==========================================
LOG_BUFFER = deque(maxlen=200)


class InMemoryLogHandler(logging.Handler):
    """Guarda los registros de log en memoria para el endpoint /logs."""

    def emit(self, record):
        msg = self.format(record)
        LOG_BUFFER.append(msg)


formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos y conserva el historial por defecto."""

    await init_db()
    logger.info("[BD] Motor activo: %s", backend_activo())

    limpieza_task = None
    # La purga queda desactivada por defecto para no borrar el historial compartido.
    if os.getenv("ENABLE_TASK_CLEANUP", "0") == "1":
        limpieza_task = asyncio.create_task(tarea_limpieza_24h(intervalo_segundos=3600))

    try:
        yield
    finally:
        if limpieza_task is not None:
            limpieza_task.cancel()
            with suppress(asyncio.CancelledError):
                await limpieza_task
        await close_db()


app = FastAPI(
    title="Evaluador de URL",
    lifespan=lifespan,
)


def origenes_permitidos():
    locales = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    publicados = [
        origen.strip().rstrip("/")
        for origen in os.getenv("CORS_ORIGINS", "").split(",")
        if origen.strip()
    ]

    return locales + publicados


app.add_middleware(
    CORSMiddleware,
    allow_origins=origenes_permitidos(),
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)


@app.get("/health", tags=["Monitoreo"])
def salud():
    return {
        "status": "ok",
        "commit": os.getenv("RENDER_GIT_COMMIT", "local"),
    }


class SolicitudAnalisis(BaseModel):
    url: HttpUrl


# ==========================================
# 3. PROCESAMIENTO CON MEDICIÓN DE TIEMPOS
# ==========================================
async def ejecutar_analisis(tarea_id: str, url: str):
    logger.info(
        f"[TAREA {tarea_id}] Iniciando análisis asíncrono para: {url}"
    )
    t_inicio = time.perf_counter()

    try:
        resultado = await procesar_analisis(url)
        duracion = time.perf_counter() - t_inicio

        logger.debug(
            f"[PERFORMANCE] Tarea {tarea_id} finalizada en {duracion:.4f}s"
        )

        # Persistir resultado exitoso en la base compartida
        await guardar_tarea_resultado(
            tarea_id=tarea_id,
            estado="completado",
            duracion=duracion,
            resultado=resultado,
        )

    except Exception as e:
        duracion = time.perf_counter() - t_inicio

        logger.exception(
            f"[ERROR] Falló el análisis de la tarea {tarea_id} "
            f"tras {duracion:.4f}s: {e}"
        )

        # Persistir error en la base compartida
        await guardar_tarea_resultado(
            tarea_id=tarea_id,
            estado="error",
            duracion=duracion,
            mensaje="No fue posible completar el análisis.",
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

    logger.info(
        f"Petición recibida en /analizar. Asignado ID: {tarea_id}"
    )

    # La evaluación queda guardada en la base de datos compartida.
    await guardar_tarea_inicial(
        tarea_id,
        estado="en_proceso",
        url=str(solicitud.url),
    )

    background_tasks.add_task(
        ejecutar_analisis,
        tarea_id,
        str(solicitud.url),
    )

    return {
        "id": tarea_id,
        "estado": "en_proceso",
    }


@app.get("/tareas", tags=["Historial compartido"])
async def consultar_historial(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Devuelve evaluaciones compartidas, ordenadas de más recientes a antiguas."""
    return await listar_tareas(limit=limit, offset=offset)


@app.get("/tareas/{tarea_id}")
async def consultar_tarea(tarea_id: str):
    # Consultar estado y resultado en la base de datos compartida.
    tarea = await obtener_tarea_por_id(tarea_id)

    if tarea is None:
        logger.warning(
            f"Consulta a tarea inexistente: {tarea_id}"
        )

        raise HTTPException(
            status_code=404,
            detail="La revisión no está disponible en esta base de datos.",
        )

    return tarea


@app.get("/logs", tags=["Monitoreo"])
def obtener_logs():
    """Devuelve los últimos 200 registros de log del servidor."""

    return {
        "total_registros": len(LOG_BUFFER),
        "logs": list(LOG_BUFFER),
    }