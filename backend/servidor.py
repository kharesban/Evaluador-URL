import logging
import os
import sys
import time
from collections import deque
from pathlib import Path
from uuid import uuid4


from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
from pathlib import Path

ruta_env = Path(__file__).resolve().parent / ".env"
load_dotenv(ruta_env, override=True)

# ==========================================
# 1. CONFIGURACIÓN DE LOGS EN MEMORIA Y CONSOLA
# ==========================================
# Mantiene hasta 200 eventos en memoria para el endpoint /logs
LOG_BUFFER = deque(maxlen=200)

class InMemoryLogHandler(logging.Handler):
    """Handler personalizado para guardar los registros de log en memoria."""
    def emit(self, record):
        msg = self.format(record)
        LOG_BUFFER.append(msg)

# Formateador global
formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Handlers: Consola + Memoria
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

app = FastAPI(title="Evaluador de URL")


def origenes_permitidos():
    locales = ["http://localhost:5173", "http://127.0.0.1:5173"]
    publicados = [origen.strip().rstrip("/") for origen in os.getenv("CORS_ORIGINS", "").split(",") if origen.strip()]
    return locales + publicados


app.add_middleware(
    CORSMiddleware,
    allow_origins=origenes_permitidos(),
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

# Almacenamiento temporal de tareas en memoria
tareas = {}


@app.get("/health", tags=["Monitoreo"])
def salud():
    return {"status": "ok", "commit": os.getenv("RENDER_GIT_COMMIT", "local")}


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

        tareas[tarea_id] = {
            "id": tarea_id,
            "estado": "completado",
            "tiempo_ejecucion_seg": round(duracion, 4),
            "resultado": resultado,
        }
    except Exception as e:
        duracion = time.perf_counter() - t_inicio
        logger.exception(f"[ERROR] Falló el análisis de la tarea {tarea_id} tras {duracion:.4f}s: {e}")

        tareas[tarea_id] = {
            "id": tarea_id,
            "estado": "error",
            "tiempo_ejecucion_seg": round(duracion, 4),
            "mensaje": "No fue posible completar el análisis.",
        }


# ==========================================
# 4. ENDPOINTS DE LA API
# ==========================================
@app.post("/analizar", status_code=202)
def iniciar_analisis(
    solicitud: SolicitudAnalisis,
    background_tasks: BackgroundTasks,
):
    tarea_id = str(uuid4())
    logger.info(f"Petición recibida en /analizar. Asignado ID: {tarea_id}")

    tarea = {
        "id": tarea_id,
        "estado": "en_proceso",
    }
    tareas[tarea_id] = tarea

    background_tasks.add_task(
        ejecutar_analisis,
        tarea_id,
        str(solicitud.url),
    )

    return tarea


@app.get("/tareas/{tarea_id}")
def consultar_tarea(tarea_id: str):
    tarea = tareas.get(tarea_id)

    if tarea is None:
        logger.warning(f"Consulta a tarea inexistente: {tarea_id}")
        raise HTTPException(
            status_code=404,
            detail="La tarea no existe o el servidor se reinició.",
        )

    return tarea


@app.get("/logs", tags=["Monitoreo"])
def obtener_logs():
    """Devuelve los últimos 200 registros de log generados por el servidor."""
    return {
        "total_registros": len(LOG_BUFFER),
        "logs": list(LOG_BUFFER)
    }
