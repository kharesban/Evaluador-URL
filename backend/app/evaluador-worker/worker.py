import asyncio
import json
import logging
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Configuración del logger para auditoría
logger = logging.getLogger("servidor_logger")

# Asegurar la ruta raíz del proyecto para importaciones
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.gestor_fuentes import analizar_fuentes
from app.validador.similitud_dominio import analizar_similitud
from app.validador.analisisUrl import normalizacion_analisis_url
from clasificacion import calcular_riesgo


async def procesar_analisis(url: str) -> dict:
    inicio_total = time.perf_counter()
    ruta_env = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(ruta_env, override=True)

    # 1. Normalización, sintaxis y métricas léxicas
    t0_norm = time.perf_counter()
    es_valido, url_str, metricas, error_validacion = normalizacion_analisis_url(url)
    dt_norm = round(time.perf_counter() - t0_norm, 3)
    logger.info(f"[Normalización y Métricas] Tiempo: {dt_norm}s")

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

    # 2. Diagnóstico externo asíncrono (VirusTotal, PhishTank, Safe Browsing, SSL, WHOIS)
    resultado = await analizar_fuentes(url_str)

    # Registro en consola/logs de los tiempos individuales devueltos por gestor_fuentes
    fuentes = resultado.get("fuentes", {})
    modulos_cumplen = True

    for nombre_fuente, datos in fuentes.items():
        # Extraer el tiempo retornado o calculado por cada módulo
        dt_modulo = datos.get("tiempo_ejecucion_seg") or datos.get("tiempo_seg") or 0.0
        alerta = " ⚠️ [EXCEDE 10s]" if dt_modulo > 10.0 else ""
        if dt_modulo > 10.0:
            modulos_cumplen = False
        logger.info(f"[{nombre_fuente.upper()}] Tiempo de ejecución: {dt_modulo}s | Estado: {datos.get('estado')}{alerta}")

    # 3. Análisis de similitud de dominio (Typosquatting)
    t0_sim = time.perf_counter()
    try:
        hallazgos = analizar_similitud(url_str)
    except Exception as e:
        logger.error(f"[Typosquatting] Error en análisis de similitud: {e}")
        hallazgos = None
    dt_sim = round(time.perf_counter() - t0_sim, 3)
    logger.info(f"[Typosquatting] Tiempo: {dt_sim}s")

    # 4. Adjuntar métricas y calcular la puntuación de riesgo final
    resultado["metricas_lexicas"] = metricas
    resultado["hallazgos_similitud"] = hallazgos
    resultado["riesgo"] = calcular_riesgo(
        resultado["fuentes"],
        hallazgos,
        metricas_lexicas=metricas
    )

    # Medición y evaluación del tiempo total del worker
    tiempo_total = round(time.perf_counter() - inicio_total, 3)
    total_cumple = tiempo_total < 20.0
    cumple_metricas = modulos_cumplen and total_cumple

    logger.info(
        f"[RESUMEN AUDITORÍA] Tiempo Total: {tiempo_total}s | "
        f"Métricas internas (Máx 10s/módulo, <20s Total): "
        f"{'✅ CUMPLE' if cumple_metricas else '❌ INCUMPLE'}"
    )

    resultado["tiempo_ejecucion_total_seg"] = tiempo_total
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