import asyncio
import importlib
import inspect
from time import monotonic
from urllib.parse import urlparse

TIEMPO_LIMITE = 4.0

async def _ejecutar_fuente_async(modulo_str: str, funcion_str: str, argumento: str) -> dict:
    try:
        modulo = importlib.import_module(modulo_str)
        func = getattr(modulo, funcion_str)

        if inspect.iscoroutinefunction(func):
            tarea = func(argumento)
        else:
            loop = asyncio.get_running_loop()
            tarea = loop.run_in_executor(None, func, argumento)

        datos = await asyncio.wait_for(tarea, timeout=TIEMPO_LIMITE)

        if not isinstance(datos, dict):
            return {"estado": "error", "error": "Respuesta no válida"}
        
        # Si el dict tiene una clave 'error' con texto descriptivo real, lo tratamos como error
        error_val = datos.get("error")
        if error_val is not None and error_val is not False and str(error_val).strip() != "":
            return {"estado": "error", "error": str(error_val)}
        
        # Si la fuente respondió exitosamente
        return {"estado": "ok", "datos": datos}

    except asyncio.TimeoutError:
        return {"estado": "timeout", "error": "Se agotó el tiempo de espera"}
    except Exception as error:
        return {"estado": "error", "error": type(error).__name__}


async def analizar_fuentes(url: str) -> dict:
    inicio = monotonic()
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

    tareas = {
        nombre: _ejecutar_fuente_async(mod, func, arg)
        for nombre, (mod, func, arg) in fuentes.items()
    }

    nombres = list(tareas.keys())
    respuestas = await asyncio.gather(*tareas.values(), return_exceptions=True)

    resultados = {}
    for nombre, resp in zip(nombres, respuestas):
        if isinstance(resp, Exception):
            resultados[nombre] = {"estado": "error", "error": str(resp)}
        else:
            resultados[nombre] = resp

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
        "duracion_segundos": round(monotonic() - inicio, 3),
        "fuentes": resultados
    }