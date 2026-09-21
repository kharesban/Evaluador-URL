import httpx
from app.confQueue.ConfigApi import settings

GOOGLE_URL = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={settings.GOOGLE_KEY}"

async def consultar_google_safe_browsing(url: str) -> dict:
    if not settings.GOOGLE_KEY:
        return {"error": "Google API Key no configurada en .env"}

    payload = {
        "client": {
            "clientId": "evaluador-url-mvp",
            "clientVersion": "1.0.0"
        },
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}]
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(GOOGLE_URL, json=payload, timeout=5.0)
            data = response.json()
            
            es_maliciosa = "matches" in data
            return {
                "es_maliciosa": es_maliciosa,
                "amenazas": data.get("matches", []),
                "error": None
            }
        except Exception as e:
            return {"error": f"Error al consultar Google Safe Browsing: {str(e)}"}