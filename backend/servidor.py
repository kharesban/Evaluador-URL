import logging
import sys
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

carpeta_worker = (
    Path(__file__).resolve().parent / "app" / "evaluador-worker"
)
sys.path.insert(0, str(carpeta_worker))

from worker import procesar_analisis

app = FastAPI(title="Evaluador de URL")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

# Guarda temporalmente el estado y resultado de cada tarea.
tareas = {}


class SolicitudAnalisis(BaseModel):
    url: HttpUrl


def ejecutar_analisis(tarea_id, url):
    try:
        resultado = procesar_analisis(url)

        tareas[tarea_id] = {
            "id": tarea_id,
            "estado": "completado",
            "resultado": resultado,
        }
    except Exception:
        logging.exception("Falló el análisis de la tarea %s", tarea_id)

        tareas[tarea_id] = {
            "id": tarea_id,
            "estado": "error",
            "mensaje": "No fue posible completar el análisis.",
        }


@app.post("/analizar", status_code=202)
def iniciar_analisis(
    solicitud: SolicitudAnalisis,
    background_tasks: BackgroundTasks,
):
    tarea_id = str(uuid4())

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
        raise HTTPException(
            status_code=404,
            detail="La tarea no existe o el servidor se reinició.",
        )

    return tarea