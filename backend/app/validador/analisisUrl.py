import socket #consulta servidores DNS
from urllib.parse import urlparse #descompone la url en sus partes
from pydantic import BaseModel, HttpUrl, ValidationError, field_validator

class SolicitudAnalisisUrl(BaseModel):
    url: HttpUrl

    @field_validator('url')
    @classmethod
    def validar_tld_dominio(cls, validador: HttpUrl) -> HttpUrl:
        host = validador.host
        # 1. Exige que tenga al menos un punto para tener TLD (.top, .xyz, .com, etc.)
        if host and '.' not in host:
            raise ValueError("El dominio ingresado carece de extensión/TLD válida (ej. .com, .top, .xyz).")
        return validador

def verificar_existencia_dns(url_str: str) -> bool:
    """Intenta resolver la dirección IP del dominio en Internet."""
    try:
        dominio = urlparse(url_str).netloc
        socket.gethostbyname(dominio)
        return True
    except socket.gaierror:
        # El dominio no existe en los registros DNS mundiales
        return False

def normalizacion_analisis_url(urlE: str):
    url_limpia = urlE.strip()
    if not (url_limpia.startswith('http://') or url_limpia.startswith('https://')):
        url_limpia = "https://" + url_limpia
    
    try:
        # Paso A: Validación y normalización sintáctica con Pydantic
        url_normalizada = SolicitudAnalisisUrl(url=url_limpia)
        url_str = str(url_normalizada.url)

        # Paso B: Verificación de existencia real en DNS
        if not verificar_existencia_dns(url_str):
            return False, None, "El dominio no existe o no se pudo resolver en el sistema DNS."

        return True, url_str, None

    except ValidationError as e:
        return False, None, e.errors()[0]['msg']