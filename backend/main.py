import asyncio
import time
from urllib.parse import urlparse

# Importaciones del validador y diagnóstico externo
from app.validador.analisisUrl import normalizacion_analisis_url
from app.validador.similitud_dominio import analizar_similitud
from app.diagnostico_externo import (
    consultar_google_safe_browsing,
    verificar_ssl,
    consultar_virustotal,
    obtener_info_whois
)

async def ejecutar_diagnostico_completo(url_normalizada: str):
    """Ejecuta las consultas externas garantizando un timeout máximo por fuente (HU 5, HU 6, HU 7)."""
    dominio = urlparse(url_normalizada).netloc

    print("\n" + "=" * 50)
    print(" INICIANDO DIAGNÓSTICO EXTERNO DE SEGURIDAD")
    print("=" * 50)

    # --- HU 6: METADATOS WHOIS ---
    print("\nConsultando Información WHOIS...")
    t0 = time.time()
    info_whois = obtener_info_whois(dominio)
    t_whois = round(time.time() - t0, 2)
    print(f"  - Tiempo de respuesta: {t_whois}s")
    print(f"  - Registrador: {info_whois.get('registrador', 'N/A')}")
    print(f"  - Antigüedad del dominio: {info_whois.get('dias_antiguedad', 'Desconocido')} días")

    # --- HU 7: CERTIFICADO SSL/TLS ---
    print("\nValidando Certificado SSL/TLS...")
    t0 = time.time()
    info_ssl = verificar_ssl(dominio)
    t_ssl = round(time.time() - t0, 2)
    print(f"  - Tiempo de respuesta: {t_ssl}s")
    print(f"  - Certificado Válido: {'✅ Sí' if info_ssl.get('valido') else '❌ No'}")
    print(f"  - Emisor: {info_ssl.get('emisor', 'N/A')}")
    if info_ssl.get('error'):
        print(f"  - Alerta de Seguridad SSL: {info_ssl['error']}")

    # --- HU 5: FUENTES DE REPUTACIÓN EXTERNA (Timeout máx 10s por fuente) ---
    print("\nConsultando Reputación Externa...")

    # 1. Google Safe Browsing
    t0 = time.time()
    try:
        res_google = await asyncio.wait_for(consultar_google_safe_browsing(url_normalizada), timeout=10.0)
        t_google = round(time.time() - t0, 2)
        estado_g = "🚨 MALICIOSA" if res_google.get("es_maliciosa") else "✅ Limpia"
        print(f"  - Google Safe Browsing ({t_google}s): {estado_g}")
    except asyncio.TimeoutError:
        print("  - Google Safe Browsing: ⚠️ TIMEOUT (>10s)")

    # 2. VirusTotal
    t0 = time.time()
    try:
        res_vt = await asyncio.wait_for(consultar_virustotal(url_normalizada), timeout=10.0)
        t_vt = round(time.time() - t0, 2)
        maliciosos = res_vt.get("maliciosos", 0)
        estado_vt = f"🚨 {maliciosos} motores la marcan como maliciosa" if maliciosos > 0 else "✅ Sin reportes"
        print(f"  - VirusTotal ({t_vt}s): {estado_vt}")
    except asyncio.TimeoutError:
        print("  - VirusTotal: ⚠️ TIMEOUT (>10s)")

    print("\n" + "=" * 50 + "\n")

def menu():
    print("""Prueba de análisis de URLs
          Para iniciar ingresa URL o si quieres salir escribir 'salir' para finalizar""")
    
    while True:
        url_entrada = input("\nIngrese la URL para analizar: ")
        
        if url_entrada.strip().lower() == "salir":
            print("Hasta pronto, vuelve cuando quieras analizar una URL...")
            break 
        elif not url_entrada.strip():
            print("Parece que no has ingresado ninguna URL... ")
            continue
        else:
            # 1. Validación inicial y análisis estructural de la URL (HU 8)
            es_valido, url_normalizada, metricas, error = normalizacion_analisis_url(url_entrada)
            
            if es_valido:
                print("\n✅ ESTADO: URL VÁLIDA Y NORMALIZADA")
                print(f"  - Entrada original:  {url_entrada}")
                print(f"  - URL Normalizada:   {url_normalizada}")
                
                # Extraer el dominio limpio
                dominio_extraido = urlparse(url_normalizada).netloc
                
                # Evaluación de Typosquatting / Similitud de Dominio
                resultado_similitud = analizar_similitud(dominio_extraido)

                # Despliegue de HU 8 (Estructura léxica + Typosquatting)
                if metricas:
                    print("\nAnálisis Léxico / Estructura:")
                    print(f"  - Longitud total: {metricas['longitud_total']} caracteres")
                    print(f"  - Cantidad de subdominios: {metricas['cantidad_subdominios']}")
                    print(f"  - Símbolos especiales: {metricas['simbolos_sospechosos']}")
                    
                    # Mostrar alerta de Typosquatting si la función detectó algo
                    if resultado_similitud and resultado_similitud.get("es_sospechoso"):
                        print(f"  - 🚨 Alerta de Typosquatting: {resultado_similitud.get('mensaje')}")
                    else:
                        print("  - ✅ No se detectó suplantación visual de marcas conocidas")

                    if metricas['banderas_alerta']:
                        print(f"  - ⚠️ Alertas de estructura: {', '.join(metricas['banderas_alerta'])}")
                    else:
                        print("  - ✅ Estructura léxica dentro de parámetros normales")

                # 2. Ejecutar HU 5, HU 6 y HU 7 (Diagnóstico Externo)
                asyncio.run(ejecutar_diagnostico_completo(url_normalizada))
                
            else:
                print("\n❌ ESTADO: URL INVÁLIDA")
                print(f"  - Entrada original:  {url_entrada}")
                print(f"  - Causa del rechazo: {error}")
                print("-" * 40 + "\n")

if __name__ == "__main__":
    menu()