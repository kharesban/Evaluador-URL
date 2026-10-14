import asyncio
import datetime
import httpx
from urllib.parse import urlparse

async def obtener_info_whois(dominio: str) -> dict:
    if "://" in dominio:
        dominio = urlparse(dominio).hostname or dominio

    partes = dominio.split(".")
    dominio_raiz = ".".join(partes[-2:]) if len(partes) > 2 and partes[-1] in ["io", "com", "co", "net", "org"] else dominio

    endpoints_rdap = [
        f"https://rdap.org/domain/{dominio_raiz}",
        f"https://rdap.verisign.com/com/v1/domain/{dominio_raiz}" if dominio_raiz.endswith(".com") else None
    ]

    async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
        for url_rdap in filter(None, endpoints_rdap):
            try:
                resp = await client.get(url_rdap)
                if resp.status_code == 200:
                    data = resp.json()
                    events = data.get("events", [])
                    
                    # Buscar cualquier evento asociado a la fecha de creación/registro inicial
                    for event in events:
                        accion = str(event.get("eventAction", "")).lower()
                        if accion in ["registration", "created", "transfer", "last changed"]:
                            fecha_raw = event.get("eventDate", "")
                            if fecha_raw:
                                fecha_str = fecha_raw.split("T")[0]
                                fecha_dt = datetime.datetime.strptime(fecha_str, "%Y-%m-%d")
                                dias = (datetime.datetime.now() - fecha_dt).days
                                return {
                                    "estado": "ok",
                                    "datos": {
                                        "dias_antiguedad": max(dias, 0)
                                    }
                                }
            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.RequestError):
                continue

    return {
        "estado": "error",
        "datos": None,
        "mensaje": "No se pudo obtener información de antigüedad (Timeout o evento no encontrado)"
    }