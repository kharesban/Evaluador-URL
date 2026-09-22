import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Permitir que Python encuentre la carpeta app dentro de backend.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.gestor_fuentes import analizar_fuentes
from app.validador.similitud_dominio import analizar_similitud
from clasificacion import calcular_riesgo


def procesar_analisis(url):
    ruta_env = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(ruta_env, override=True)

    resultado = analizar_fuentes(url)

    try:
        hallazgos = analizar_similitud(url)
    except ValueError:
        hallazgos = None

    resultado["hallazgos_similitud"] = hallazgos
    resultado["riesgo"] = calcular_riesgo(
        resultado["fuentes"],
        hallazgos,
    )

    return resultado

# Este bloque es necesario para crear los procesos en Windows.
if __name__ == "__main__":
    try:
        url = input("Ingresa una URL: ")
        resultado = procesar_analisis(url)

        print(json.dumps(resultado, indent=2, ensure_ascii=False))

    except ValueError as error:
        print("No se pudo analizar:", error)