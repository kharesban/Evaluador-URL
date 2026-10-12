import asyncio
import importlib
import inspect
import logging
import time
from time import monotonic, perf_counter
from urllib.parse import urlparse

# Logger principal de la aplicación para que los registros aparezcan en /logs
logger = logging.getLogger("backend_app")

TIEMPO_LIMITE = 4.0

async def _ejecutar_fuente_async(modulo_str: str, funcion_str: str, argumento: str, nombre_fuente: str) -> dict:
    t0 = perf_counter()
    try:
        modulo = importlib.import_module(modulo_str)
        func = getattr(modulo, funcion_str)

        if inspect.iscoroutinefunction(func):
            tarea = func(argumento)
        else:
            loop = asyncio.get_running_loop()
            tarea = loop.run_in_executor(None, func, argumento)

        datos = await asyncio.wait_for(tarea, timeout=TIEMPO_LIMITE)
        dt = round(perf_counter() - t0, 3)

        if not isinstance(datos, dict):
            res = {"estado": "error", "error": "Respuesta no válida", "tiempo_ejecucion_seg": dt}
            logger.error(f"[{nombre_fuente.upper()}] Tiempo: {dt}s | Estado: error (Respuesta no válida)")
            return res
        
        # Si el dict tiene una clave 'error' con texto descriptivo real, lo tratamos como error
        error_val = datos.get("error")
        if error_val is not None and error_val is not False and str(error_val).strip() != "":
            res = {"estado": "error", "error": str(error_val), "tiempo_ejecucion_seg": dt}
            logger.error(f"[{nombre_fuente.upper()}] Tiempo: {dt}s | Estado: error ({error_val})")
            return res
        
        # Si la fuente respondió exitosamente
        res = {"estado": "ok", "datos": datos, "tiempo_ejecucion_seg": dt}
        alerta = " ⚠️ [EXCEDE 10s]" if dt > 10.0 else ""
        logger.info(f"[{nombre_fuente.upper()}] Tiempo de ejecución: {dt}s | Estado: ok{alerta}")
        return res

    except asyncio.TimeoutError:
        dt = round(perf_counter() - t0, 3)
        res = {"estado": "timeout", "error": "Se agotó el tiempo de espera", "tiempo_ejecucion_seg": dt}
        logger.warning(f"[{nombre_fuente.upper()}] Tiempo: {dt}s | Estado: timeout")
        return res
    except Exception as error:
        dt = round(perf_counter() - t0, 3)
        res = {"estado": "error", "error": type(error).__name__, "tiempo_ejecucion_seg": dt}
        logger.error(f"[{nombre_fuente.upper()}] Tiempo: {dt}s | Estado: error ({type(error).__name__})")
        return res


async def analizar_fuentes(url: str) -> dict:
    inicio = monotonic()
    inicio_perf = perf_counter()
    url = str(url).strip()

    if "://" not in url:
        url = "https://" + url

    dominio = urlparse(url).hostname

    if not dominio:
        raise ValueError("La URL debe contener un dominio válido")

    base = "app.diagnostico_externo."

    fuentes = {
        "virustotal": (
            base + "virusTotal_module",
            "consultar_virustotal",
            url
        ),
        "safe_browsing": (
            base + "safeBrowsing_module",
            "consultar_google_safe_browsing",
            url
        ),
        "phishtank": (
            base + "phishTank_module",
            "consultar_phishtank",
            url
        ),
        "ssl": (
            base + "SSL_module",
            "verificar_ssl",
            dominio
        ),
        "whois": (
            base + "whois_module",
            "obtener_info_whois",
            dominio
        )
    }

    # Pasamos el nombre de la fuente para un etiquetado preciso en logs
    tareas = {
        nombre: _ejecutar_fuente_async(mod, func, arg, nombre)
        for nombre, (mod, func, arg) in fuentes.items()
    }

    nombres = list(tareas.keys())
    respuestas = await asyncio.gather(*tareas.values(), return_exceptions=True)

    resultados = {}
    modulos_ok = True

    for nombre, resp in zip(nombres, respuestas):
        if isinstance(resp, Exception):
            resultados[nombre] = {"estado": "error", "error": str(resp), "tiempo_ejecucion_seg": 0.0}
            modulos_ok = False
        else:
            resultados[nombre] = resp
            if resp.get("tiempo_ejecucion_seg", 0.0) > 10.0:
                modulos_ok = False

    tiempo_total = round(perf_counter() - inicio_perf, 3)
    total_ok = tiempo_total < 20.0
    cumple_todas = modulos_ok and total_ok

    logger.info(
        f"[RESUMEN PERFORMANCE FUENTES] Total: {tiempo_total}s | "
        f"Métricas (Max 10s/módulo, <20s Total): {'✅ CUMPLE' if cumple_todas else '❌ INCUMPLE'}"
    )

    disponibles = sum(
        1 for r in resultados.values() if r.get("estado") == "ok"
    )

    if disponibles == 0:
        estado = "sin_resultados"
    elif disponibles == len(fuentes):
        estado = "completo"
    else:
        estado = "parcial"

    return {
        "estado": estado,
        "duracion_segundos": tiempo_total,
        "fuentes": resultados
    }