import logging
from urllib.parse import urlparse

from rapidfuzz.distance import DamerauLevenshtein


DOMINIOS_OFICIALES = ["google.com", "facebook.com", "microsoft.com"]


def analizar_similitud(url):
    # Obtener el dominio de la URL.
    url = url.strip()
    if "://" not in url:
        url = "https://" + url

    dominio = urlparse(url).hostname
    if not dominio:
        raise ValueError("Debes ingresar una URL con dominio.")

    dominio = dominio.lower().rstrip(".").removeprefix("www.")

    # No alertar si coincide con un dominio oficial o sus subdominios.
    for oficial in DOMINIOS_OFICIALES:
        if dominio == oficial or dominio.endswith("." + oficial):
            return []

    hallazgos = []

    for oficial in DOMINIOS_OFICIALES:
        # Comparar la parte final aunque la URL tenga subdominios.
        # Ejemplo: sub.googel.com -> googel.com
        cantidad_partes = len(oficial.split("."))
        dominio_comparable = ".".join(
            dominio.split(".")[-cantidad_partes:]
        )

        distancia = DamerauLevenshtein.distance(
            dominio_comparable, oficial
        )

        # Una o dos ediciones de diferencia generan una alerta.
        if 1 <= distancia <= 2:
            similitud = DamerauLevenshtein.normalized_similarity(
                dominio_comparable, oficial
            )

            hallazgos.append({
                "dominio": dominio,
                "referencia": oficial,
                "similitud": round(similitud * 100, 2),
                "motivo": "Posible typosquatting",
            })

            logging.warning(
                "Posible suplantación: %s → %s", dominio, oficial
            )

    return hallazgos