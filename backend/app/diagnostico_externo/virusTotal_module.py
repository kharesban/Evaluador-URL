import base64
import httpx
from app.confQueue.ConfigApi import settings

VIRUSTOTAL_URL = "https://www.virustotal.com/api/v3/urls/"

def _url_to_vt_id(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode()).decode().strip("=")

async def consultar_virustotal(url: str) -> dict:
    if not settings.VIRUSTOTAL_KEY:
        return {"error": "VirusTotal API Key no configurada en .env"}

    url_id = _url_to_vt_id(url)
    headers = {"x-apikey": settings.VIRUSTOTAL_KEY}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{VIRUSTOTAL_URL}{url_id}", headers=headers, timeout=5.0)
            
            if response.status_code == 404:
                return {
                    "es_conocida": False, 
                    "maliciosos": 0, 
                    "resumen": "URL no analizada previamente en VirusTotal",
                    "error": None
                }
                
            data = response.json()
            stats = data["data"]["attributes"]["last_analysis_stats"]
            
            return {
                "es_conocida": True,
                "maliciosos": stats.get("malicious", 0),
                "sospechosos": stats.get("suspicious", 0),
                "inofensivos": stats.get("harmless", 0),
                "error": None
            }
        except Exception as e:
            return {"error": f"Error al consultar VirusTotal: {str(e)}"}