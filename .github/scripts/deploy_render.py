"""Solicitar ambos despliegues y verificar que sirvan el commit aprobado."""
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


def leer_json(url):
    solicitud = Request(url, headers={"Cache-Control": "no-cache", "User-Agent": "Evaluador-URL-CD"})
    with urlopen(solicitud, timeout=15) as respuesta:
        return json.load(respuesta)


def solicitar_despliegue(hook, commit):
    partes = urlsplit(hook)
    if partes.scheme != "https" or partes.hostname != "api.render.com" or not partes.path.startswith("/deploy/"):
        raise ValueError("El deploy hook debe ser una URL HTTPS de api.render.com/deploy/")
    parametros = [(k, v) for k, v in parse_qsl(partes.query) if k != "ref"]
    parametros.append(("ref", commit))
    url = urlunsplit(partes._replace(query=urlencode(parametros)))
    # No imprimir el hook, su respuesta ni excepciones que puedan incluir la clave.
    solicitud = Request(url, method="POST")
    with urlopen(solicitud, timeout=30) as respuesta:
        if respuesta.status not in (200, 202):
            raise RuntimeError("Render no aceptó la solicitud de despliegue")


def esperar_version(base, ruta, commit, nombre, limite_segundos=600):
    limite = time.monotonic() + limite_segundos
    while time.monotonic() < limite:
        url = f"{base}{ruta}?{urlencode({'commit': commit, 't': time.time_ns()})}"
        try:
            datos = leer_json(url)
            if datos.get("commit") == commit and (ruta != "/health" or datos.get("status") == "ok"):
                print(f"OK: {nombre} está sirviendo el commit aprobado.", flush=True)
                return
        except (URLError, TimeoutError, OSError, ValueError, AttributeError):
            pass  # El servicio anterior puede seguir activo mientras termina el build.
        print(f"Esperando que {nombre} publique la versión nueva…", flush=True)
        time.sleep(10)
    raise TimeoutError(f"{nombre} no publicó el commit esperado en {limite_segundos} segundos")


def url_publica(nombre):
    valor = os.environ.get(nombre, "").strip().rstrip("/")
    partes = urlsplit(valor)
    if partes.scheme != "https" or not partes.netloc or partes.username or partes.password or partes.query or partes.fragment or partes.path:
        raise ValueError(f"{nombre} debe contener solo el origen HTTPS público, sin rutas ni parámetros")
    return valor


def main():
    reporte = {"commit": os.environ.get("GITHUB_SHA", ""), "estado": "error", "verificados": []}
    codigo = 1
    try:
        commit = reporte["commit"]
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError("No se recibió un GITHUB_SHA válido")
        backend = url_publica("RENDER_BACKEND_URL")
        frontend = url_publica("RENDER_FRONTEND_URL")
        hooks = [os.environ.get("RENDER_BACKEND_DEPLOY_HOOK", ""), os.environ.get("RENDER_FRONTEND_DEPLOY_HOOK", "")]
        if not all(hooks):
            raise ValueError("Faltan los dos secrets de deploy hooks")
        for nombre, hook, base, ruta in [
            ("backend", hooks[0], backend, "/health"),
            ("frontend", hooks[1], frontend, "/deploy-version.json"),
        ]:
            print(f"Solicitando despliegue de {nombre}…", flush=True)
            solicitar_despliegue(hook, commit)
            esperar_version(base, ruta, commit, nombre)
            reporte["verificados"].append(nombre)
        # Además del marcador de versión, comprobar el contrato público del backend.
        contrato = leer_json(backend + "/openapi.json")
        if not {"/analizar", "/tareas/{tarea_id}", "/logs"} <= set(contrato.get("paths", {})):
            raise RuntimeError("El backend publicado no expone las rutas esperadas")
        reporte["estado"] = "correcto"
        codigo = 0
    except Exception as error:
        # El tipo aporta diagnóstico sin filtrar el hook ni credenciales de la URL.
        print(f"ERROR: despliegue no confirmado ({type(error).__name__}). Revisa la configuración y los logs de Render.", file=sys.stderr)
    finally:
        Path("qa-results").mkdir(exist_ok=True)
        Path("qa-results/deploy.json").write_text(json.dumps(reporte, indent=2), encoding="utf-8")
        resumen = os.environ.get("GITHUB_STEP_SUMMARY")
        if resumen:
            with open(resumen, "a", encoding="utf-8") as archivo:
                archivo.write(f"## Despliegue Render\n\nCommit: `{reporte['commit']}`\n\nResultado: **{reporte['estado']}**\n\nServicios verificados: {', '.join(reporte['verificados']) or 'ninguno'}.\n")
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
