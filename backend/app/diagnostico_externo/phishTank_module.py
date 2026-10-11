# backend/app/diagnostico_externo/phishTank_module.py

import logging
from urllib.parse import quote
import httpx

logger = logging.getLogger("servidor_logger")

PHISHTANK_API_URL = "https://checkurl.phishtank.com/checkurl/"


async def consultar_phishtank(url: str) -> dict:
    """
    Consulta la API pública de PhishTank codificando correctamente las subrutas/paths.
    """
    headers = {
        "User-Agent": "phishtank/app-evaluador-url",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    url_limpia = url.strip()
    
    # Generar variaciones de la URL (con/sin barra final y http/https)
    variaciones = [url_limpia]

    if url_limpia.endswith("/"):
        variaciones.append(url_limpia.rstrip("/"))
    else:
        variaciones.append(url_limpia + "/")

    if url_limpia.startswith("https://"):
        variaciones.append("http://" + url_limpia[8:])
    elif url_limpia.startswith("http://"):
        variaciones.append("https://" + url_limpia[7:])

    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            for u in variaciones:
                # Codificar la URL para asegurar que las rutas (/mito/) se transmitan correctamente
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

                        in_database = results.get("in_database", False)
                        valid = results.get("valid", False)

                        # Si está en la base de datos o si está confirmado como valido/online
                        if in_database or valid:
                            logger.info(f"[PhishTank] Phishing confirmado para: {u}")
                            return {
                                "en_base_datos": True,
                                "es_phishing": True,
                                "esta_online": valid,
                                "phish_id": results.get("phish_id"),
                                "phish_detail_page": results.get("phish_detail_page")
                            }
                except Exception as sub_e:
                    logger.warning(f"[PhishTank] Error con la variación {u}: {sub_e}")
                    continue

        return {
            "en_base_datos": False,
            "es_phishing": False
        }

    except Exception as e:
        logger.error(f"[PhishTank] Excepción al consultar {url}: {e}")
        return {
            "en_base_datos": False,
            "es_phishing": False,
            "error": "Servicio de PhishTank no disponible"
        }