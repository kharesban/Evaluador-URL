import ssl
import socket
from datetime import datetime

def verificar_ssl(hostname: str, port: int = 443) -> dict:
    context = ssl.create_default_context()
    try:
        with socket.create_connection((hostname, port), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                
                # Formato de fecha del certificado: 'MMM DD HH:MM:SS YYYY GMT'
                fecha_exp = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                dias_restantes = (fecha_exp - datetime.now()).days
                
                issuer = dict(x[0] for x in cert.get('issuer', []))
                
                return {
                    "valido": True,
                    "emisor": issuer.get('organizationName', 'Desconocido'),
                    "dias_para_vencer": dias_restantes,
                    "error": None
                }
    except Exception as e:
        return {
            "valido": False,
            "error": f"Certificado no válido o inalcanzable: {str(e)}"
        }