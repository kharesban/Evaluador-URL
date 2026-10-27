import logging
from urllib.parse import quote
import httpx

logger = logging.getLogger("servidor_logger")

PHISHTANK_API_URL = "https://checkurl.phishtank.com/checkurl/"


async def consultar_phishtank(url: str) -> dict:
    """
    Consulta PhishTank exigiendo que el reporte esté CONFIRMADO como phishing (valid == True).
    Si valid es False o la URL no está en la base de datos, se considera limpia.
    """
    headers = {
        "User-Agent": "phishtank/app-evaluador-url",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    url_limpia = url.strip()
    
    # Probar la URL exacta y variaciones de barra final
    variaciones = [url_limpia]
    if url_limpia.endswith("/"):
        variaciones.append(url_limpia.rstrip("/"))
    else:
        variaciones.append(url_limpia + "/")

    try:
        consultas_validas = 0
        async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
            for u in variaciones:
                url_encoded = quote(u, safe="")
                body = f"url={url_encoded}&format=json"

                try:
                    respuesta = await client.post(
                        PHISHTANK_API_URL, 
                        content=body, 
                        headers=headers
                    )

                    if respuesta.status_code == 200:
                        datos = respuesta.json()
                        results = datos.get("results", {})
                        consultas_validas += 1

                        in_database = results.get("in_database", False)
                        valid = results.get("valid", False) # True si PhishTank confirmó que ES phishing

                        # ÚNICAMENTE si PhishTank confirmó que es un PHISHING VÁLIDO
                        if in_database is True and valid is True:
                            logger.info(f"[PhishTank] Phishing verificado y confirmado para: {u}")
                            return {
                                "en_base_datos": True,
                                "es_phishing": True,
                                "esta_online": results.get("in_database", True),
                                "phish_id": results.get("phish_id"),
                                "phish_detail_page": results.get("phish_detail_page")
                            }

                except Exception as sub_e:
                    logger.warning(f"[PhishTank] Error evaluando variación {u}: {sub_e}")
                    continue

        if consultas_validas == 0:
            return {
                "en_base_datos": False,
                "es_phishing": False,
                "error": "Servicio de PhishTank no disponible",
            }

        # Si no está en la base de datos O si estuvo reportado pero 'valid' es False (falso reporte)
        return {
            "en_base_datos": False,
            "es_phishing": False,
            "esta_online": False
        }

    except Exception as e:
        logger.error(f"[PhishTank] Excepción al consultar {url}: {e}")
        return {
            "en_base_datos": False,
            "es_phishing": False,
            "error": "Servicio de PhishTank no disponible"
        }
