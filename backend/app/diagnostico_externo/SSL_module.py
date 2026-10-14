import socket
import ssl
from urllib.parse import urlparse

try:
    import certifi
    ca_file = certifi.where()
except ImportError:
    ca_file = None


def verificar_ssl(url_o_dominio: str, timeout: float = 4.0) -> dict:
    if "://" in url_o_dominio:
        hostname = urlparse(url_o_dominio).hostname or url_o_dominio
    else:
        hostname = url_o_dominio.split("/")[0].split(":")[0]

    hostname = hostname.lower().rstrip(".")

    if ca_file:
        contexto = ssl.create_default_context(cafile=ca_file)
    else:
        contexto = ssl.create_default_context()

    try:
        with socket.create_connection((hostname, 443), timeout=timeout) as sock:
            with contexto.wrap_socket(sock, server_hostname=hostname) as ssock:
                # Forzar la negociación completa
                ssock.do_handshake()
                cert = ssock.getpeercert()

                if not cert:
                    return {
                        "estado": "ok",
                        "datos": {
                            "valido": False,
                            "motivo": "El servidor no entregó un certificado de pares (peer certificate)"
                        }
                    }

                issuer_dict = dict(x[0] for x in cert.get("issuer", []))
                emisor = (
                    issuer_dict.get("organizationName")
                    or issuer_dict.get("commonName")
                    or "Desconocido"
                )

                return {
                    "estado": "ok",
                    "datos": {
                        "valido": True,
                        "emisor": emisor,
                        "hostname_analizado": hostname
                    }
                }

    except ssl.SSLCertVerificationError as e:
        return {
            "estado": "ok",
            "datos": {
                "valido": False,
                "motivo": f"Error de verificación SSL para {hostname}: {e.verify_message}"
            }
        }
    except ssl.SSLError as e:
        return {
            "estado": "ok",
            "datos": {
                "valido": False,
                "motivo": f"Error SSL: {str(e)}"
            }
        }
    except (ConnectionRefusedError, socket.gaierror):
        return {
            "estado": "ok",
            "datos": {
                "valido": False,
                "motivo": f"El puerto 443 no está disponible en {hostname}"
            }
        }
    except (socket.timeout, TimeoutError):
        return {
            "estado": "error",
            "datos": None,
            "mensaje": f"Timeout al verificar SSL en {hostname}"
        }