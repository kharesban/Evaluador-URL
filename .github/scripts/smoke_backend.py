"""Verificar el arranque real de Uvicorn sin invocar APIs externas."""
import json
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen


def main():
    proceso = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "servidor:app",
        "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8765",
    ])
    try:
        limite = time.monotonic() + 25
        while time.monotonic() < limite:
            if proceso.poll() is not None:
                raise RuntimeError("Uvicorn terminó antes de completar el arranque")
            try:
                with urlopen("http://127.0.0.1:8765/openapi.json", timeout=2) as respuesta:
                    documento = json.load(respuesta)
                assert "/analizar" in documento["paths"]
                assert "/tareas/{tarea_id}" in documento["paths"]
                print("OK: FastAPI/Uvicorn arrancó y publicó los endpoints esperados.")
                return
            except (URLError, TimeoutError):
                time.sleep(.25)
        raise TimeoutError("La API no estuvo disponible en 25 segundos")
    finally:
        proceso.terminate()
        try:
            proceso.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proceso.kill()
            proceso.wait()


if __name__ == "__main__":
    main()
