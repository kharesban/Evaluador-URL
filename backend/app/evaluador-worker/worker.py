# backend/app/evaluador-worker/worker.py

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Asegurar la ruta raíz del proyecto para importaciones
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.gestor_fuentes import analizar_fuentes
from app.validador.similitud_dominio import analizar_similitud
from app.validador.analisisUrl import normalizacion_analisis_url
from clasificacion import calcular_riesgo


async def procesar_analisis(url: str) -> dict:
    ruta_env = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(ruta_env, override=True)

    # 1. Normalización, sintaxis y métricas léxicas
    es_valido, url_str, metricas, error_validacion = normalizacion_analisis_url(url)

    # Si falla la sintaxis estricta o TLD, se aborta
    if not es_valido and "TLD" in str(error_validacion):
        raise ValueError(f"Sintaxis de URL no válida: {error_validacion}")

    # Si la URL no resolvió en DNS (sitio caído/dado de baja), aseguramos el formato https://
    if not url_str:
        url_str = url.strip()
        if not (url_str.startswith("http://") or url_str.startswith("https://")):
            url_str = "https://" + url_str
        metricas = {
            "dns_resuelto": False,
            "banderas_alerta": ["El dominio no resuelve registros DNS (sitio caído/inactivo)"]
        }

    # 2. Diagnóstico externo asíncrono en paralelo (VirusTotal, PhishTank, Safe Browsing, SSL, WHOIS)
    resultado = await analizar_fuentes(url_str)

    # 3. Análisis de similitud de dominio (Typosquatting)
    try:
        hallazgos = analizar_similitud(url_str)
    except Exception:
        hallazgos = None

    # 4. Adjuntar métricas y calcular la puntuación de riesgo final
    resultado["metricas_lexicas"] = metricas
    resultado["hallazgos_similitud"] = hallazgos
    resultado["riesgo"] = calcular_riesgo(
        resultado["fuentes"],
        hallazgos,
        metricas
    )

    return resultado


if __name__ == "__main__":
    try:
        url_input = input("Ingresa una URL para analizar: ")
        # Ejecución del bucle de eventos asíncrono
        resultado = asyncio.run(procesar_analisis(url_input))

        # Formateo y salida JSON
        print(json.dumps(resultado, indent=2, ensure_ascii=False))

    except ValueError as error:
        print("Error en el análisis:", error)