import whois
from datetime import datetime

def obtener_info_whois(domain: str) -> dict:
    try:
        w = whois.whois(domain)
        creation_date = w.creation_date
        
        if isinstance(creation_date, list):
            creation_date = creation_date[0]

        dias_antiguedad = None
        if isinstance(creation_date, datetime):
            dias_antiguedad = (datetime.now() - creation_date).days

        return {
            "registrador": w.registrar,
            "fecha_creacion": str(creation_date) if creation_date else None,
            "dias_antiguedad": dias_antiguedad,
            "error": None
        }
    except Exception as e:
        return {"error": f"No se pudo consultar WHOIS: {str(e)}"}