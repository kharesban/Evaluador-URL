"""Limpieza opcional de evaluaciones antiguas.

La aplicación no inicia esta tarea automáticamente: el historial compartido
se conserva indefinidamente salvo que el operador active explícitamente la purga.
"""

import asyncio
import logging

from .database import eliminar_tareas_antiguas

logger = logging.getLogger("backend_app")


async def tarea_limpieza_24h(intervalo_segundos: int = 3600):
    """Purga registros con más de 24 horas mientras la tarea siga activa."""
    while True:
        try:
            eliminadas = await eliminar_tareas_antiguas(24)
            if eliminadas:
                logger.info(
                    "[BD LIMPIEZA] Purgadas %s evaluaciones con antigüedad mayor a 24h.",
                    eliminadas,
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("[BD LIMPIEZA ERROR] Fallo durante la purga: %s", exc)

        await asyncio.sleep(intervalo_segundos)
