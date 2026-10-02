import asyncio
import importlib
import inspect
import multiprocessing as mp
from multiprocessing.connection import wait
from time import monotonic
from urllib.parse import urlparse

TIEMPO_LIMITE = 10


def _consultar(modulo, funcion, argumento, canal):
    """Ejecuta una fuente en un proceso separado."""
    try:
        consulta = getattr(importlib.import_module(modulo), funcion)
        datos = consulta(argumento)

        # Permite utilizar también las funciones async existentes.
        if inspect.isawaitable(datos):
            datos = asyncio.run(datos)

        if not isinstance(datos, dict):
            resultado = {
                "estado": "error",
                "error": "Respuesta no válida"
            }
        elif datos.get("error"):
            resultado = {
                "estado": "error",
                "error": str(datos["error"])
            }
        else:
            resultado = {"estado": "ok", "datos": datos}

    except Exception as error:
        resultado = {
            "estado": "error",
            "error": type(error).__name__
        }

    try:
        canal.send((monotonic(), resultado))
    finally:
        canal.close()


def gestionar_fuentes(fuentes):
    """Recoge las respuestas durante un máximo de 10 segundos."""
    inicio = monotonic()
    vencimiento = inicio + TIEMPO_LIMITE
    contexto = mp.get_context("spawn")

    procesos = []
    pendientes = {}

    resultados = {
        nombre: {
            "estado": "timeout",
            "error": "Se agotó el tiempo de espera"
        }
        for nombre in fuentes
    }

    try:
        # Iniciar las fuentes sin esperar a que termine la anterior.
        for nombre, (modulo, funcion, argumento) in fuentes.items():
            if monotonic() >= vencimiento:
                break

            receptor, emisor = contexto.Pipe(duplex=False)

            proceso = contexto.Process(
                target=_consultar,
                args=(modulo, funcion, argumento, emisor)
            )

            try:
                proceso.start()
            except Exception as error:
                receptor.close()
                proceso.close()
                resultados[nombre] = {
                    "estado": "error",
                    "error": type(error).__name__
                }
            else:
                procesos.append(proceso)
                pendientes[receptor] = nombre
            finally:
                emisor.close()

        # Recoger las respuestas que lleguen dentro del plazo.
        while pendientes:
            restante = vencimiento - monotonic()

            if restante <= 0:
                break

            for canal in wait(list(pendientes), timeout=restante):
                nombre = pendientes.pop(canal)

                try:
                    finalizacion, resultado = canal.recv()

                    if finalizacion <= vencimiento:
                        resultados[nombre] = resultado

                except (EOFError, OSError):
                    resultados[nombre] = {
                        "estado": "error",
                        "error": "Proceso sin respuesta"
                    }
                finally:
                    canal.close()

    finally:
        # Cerrar los procesos pendientes, incluso si una fuente se bloquea.
        for proceso in procesos:
            if proceso.is_alive():
                proceso.terminate()

        for proceso in procesos:
            proceso.join(timeout=0.1)

            if proceso.is_alive():
                proceso.kill()
                proceso.join(timeout=0.1)

            if not proceso.is_alive():
                proceso.close()

        for canal in pendientes:
            canal.close()

    disponibles = sum(
        resultado["estado"] == "ok"
        for resultado in resultados.values()
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


def analizar_fuentes(url):
    """Prepara las llamadas a los módulos de tus compañeros."""
    url = str(url).strip()

    if "://" not in url:
        url = "https://" + url

    dominio = urlparse(url).hostname

    if not dominio:
        raise ValueError("La URL debe contener un dominio")

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

    return gestionar_fuentes(fuentes)