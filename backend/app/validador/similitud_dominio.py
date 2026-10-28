import logging
from urllib.parse import urlparse
from rapidfuzz.distance import DamerauLevenshtein

DOMINIOS_OFICIALES = [
    "google.com",
    "facebook.com",
    "microsoft.com",
    "nu.com.co",
    "nu.com",
]

MARCAS_PROTEGIDAS = {
    "nu.com.co": "nu",
    "nu.com": "nu",
    "google.com": "google",
    "facebook.com": "facebook",
    "microsoft.com": "microsoft",
}


def analizar_similitud(url):
    url = url.strip()
    if "://" not in url:
        url = "https://" + url

    hostname = urlparse(url).hostname
    if not hostname:
        raise ValueError("Debes ingresar una URL con dominio.")

    hostname = hostname.lower().rstrip(".").removeprefix("www.")

    # No alertar si es el dominio oficial o un subdominio oficial
    for oficial in DOMINIOS_OFICIALES:
        if hostname == oficial or hostname.endswith("." + oficial):
            return []

    hallazgos = []
    partes_host = hostname.split(".")

    for oficial, marca in MARCAS_PROTEGIDAS.items():
        for parte in partes_host:
            if parte in ["com", "co", "io", "net", "org", "github", "gitlab", "pages"]:
                continue

            # CASO A: Para "nu", detectar uso del término como prefijo/sufijo
            if marca == "nu":
                es_sospechoso = (
                    parte.startswith("nu") and len(parte) > 2
                ) or (
                    parte.endswith("nu") and len(parte) > 2
                ) or (
                    "nu-" in parte or "-nu" in parte
                )

                if es_sospechoso:
                    # Similitud matemática real sin forzar pisos falsos
                    similitud_real = DamerauLevenshtein.normalized_similarity(parte, marca)
                    porcentaje_real = round(similitud_real * 100, 2)

                    hallazgos.append({
                        "dominio": hostname,
                        "referencia": oficial,
                        "similitud": porcentaje_real,
                        "motivo": f"El término '{parte}' incluye la marca '{marca}' de {oficial}"
                    })
                    logging.warning("Uso no autorizado de marca: %s en %s", parte, hostname)
                    break

            # CASO B: Para marcas largas (google, facebook, etc.)
            else:
                similitud_real = DamerauLevenshtein.normalized_similarity(parte, marca)
                porcentaje_real = round(similitud_real * 100, 2)

                if marca in parte and parte != marca:
                    hallazgos.append({
                        "dominio": hostname,
                        "referencia": oficial,
                        "similitud": porcentaje_real,
                        "motivo": f"El término '{parte}' contiene la marca '{marca}'"
                    })
                    break

                distancia = DamerauLevenshtein.distance(parte, marca)
                if 1 <= distancia <= 2:
                    hallazgos.append({
                        "dominio": hostname,
                        "referencia": oficial,
                        "similitud": porcentaje_real,
                        "motivo": f"El término '{parte}' se parece a '{marca}'"
                    })
                    break

        if hallazgos:
            break

    return hallazgos