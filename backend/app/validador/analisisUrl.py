import re
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
    
def extraer_metricas_lexicas(url_str: str) -> dict:
    """HU 8: Evalúa la estructura de la cadena de texto de la URL para detectar anomalías."""
    parsed = urlparse(url_str)
    host = parsed.netloc or parsed.path
    
    longitud_total = len(url_str)
    
    # Calcular subdominios ignorando el TLD y el dominio principal
    partes_host = host.split('.')
    cantidad_subdominios = len(partes_host) - 2 if len(partes_host) > 2 else 0
    
    # Detección de caracteres sospechosos comunes en ataques de phishing
    simbolos_sospechosos = len(re.findall(r'[@\-=%_?&@]', url_str))
    
    # Detección de uso directo de IP
    es_ip = bool(re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', host))

    # Banderas de alerta técnica (Criterios de Aceptación HU 8)
    banderas_alerta = []
    if longitud_total > 75:
        banderas_alerta.append("URL excesivamente larga (> 75 caracteres)")
    if cantidad_subdominios > 2:
        banderas_alerta.append("Cantidad inusual de subdominios")
    if simbolos_sospechosos > 5:
        banderas_alerta.append("Alta presencia de símbolos o caracteres especiales")
    if es_ip:
        banderas_alerta.append("Uso de dirección IP directa en lugar de nombre de dominio")

    return {
        "longitud_total": longitud_total,
        "cantidad_subdominios": max(0, cantidad_subdominios),
        "simbolos_sospechosos": simbolos_sospechosos,
        "es_ip_directa": es_ip,
        "banderas_alerta": banderas_alerta
    }    

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
            return False, None, None, "El dominio no existe o no se pudo resolver en el sistema DNS."

        # Paso C (HU 8): Extracción de métricas y alertas léxicas
        metricas = extraer_metricas_lexicas(url_str)

        # Retorna 4 valores: (es_valido, url_str, metricas, error)
        return True, url_str, metricas, None

    except ValidationError as e:
        return False, None, e.errors()[0]['msg']