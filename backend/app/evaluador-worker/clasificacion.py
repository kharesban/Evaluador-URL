PESOS = {
    "reputacion": 35,
    "antiguedad": 20,
    "ssl": 15,
    "patrones_url": 15,
    "similitud": 15,
}


def calcular_riesgo(fuentes, hallazgos_similitud, metricas_lexicas=None):
    # Un dominio que no resuelve por DNS no recibe puntuación numérica.
    if (
        isinstance(metricas_lexicas, dict)
        and metricas_lexicas.get("dns_resuelto") is False
    ):
        return {
            "puntuacion": None,
            "es_dominio_invalido": True,
            "mensaje": "La página no está registrada como un dominio válido o activo.",
            "evaluacion_completa": False,
            "cobertura_porcentaje": 0,
            "indicadores": {},
            "indicadores_faltantes": list(PESOS),
        }

    def obtener_datos(nombre):
        fuente = fuentes.get(nombre, {})
        if fuente.get("estado") == "ok":
            return fuente.get("datos", {})
        return {}

    vt = obtener_datos("virustotal")
    google = obtener_datos("safe_browsing")
    phishtank = obtener_datos("phishtank")
    ssl = obtener_datos("ssl")
    whois = obtener_datos("whois")

    indicadores = {
        "reputacion": None,
        "antiguedad": None,
        "ssl": None,
        "patrones_url": None,
        "similitud": None,
    }

    # Reputación: PhishTank solo confirma riesgo cuando es_phishing es True.
    es_phishing_pt = phishtank.get("es_phishing") is True
    es_malicioso_vt = vt.get("maliciosos", 0) > 0
    es_malicioso_gsb = google.get("es_maliciosa") is True

    if es_phishing_pt or es_malicioso_vt or es_malicioso_gsb:
        indicadores["reputacion"] = 1
    elif (
        vt.get("es_conocida") is True
        and vt.get("maliciosos") == 0
        and google.get("es_maliciosa") is False
        and phishtank.get("es_phishing") is False
    ):
        indicadores["reputacion"] = 0

    dias = whois.get("dias_antiguedad")
    if isinstance(dias, (int, float)) and dias >= 0:
        if dias < 30:
            indicadores["antiguedad"] = 1
        elif dias < 180:
            indicadores["antiguedad"] = 0.5
        else:
            indicadores["antiguedad"] = 0

    if ssl.get("valido") is True:
        indicadores["ssl"] = 0
    elif ssl.get("valido") is False:
        indicadores["ssl"] = 1

    # Una alerta aporta la mitad del riesgo de patrones; dos o más, el total.
    claves_patrones = (
        "longitud_total",
        "cantidad_subdominios",
        "simbolos_sospechosos",
        "es_ip_directa",
        "banderas_alerta",
    )
    if (
        isinstance(metricas_lexicas, dict)
        and all(clave in metricas_lexicas for clave in claves_patrones)
        and isinstance(metricas_lexicas["banderas_alerta"], list)
    ):
        indicadores["patrones_url"] = min(
            len(metricas_lexicas["banderas_alerta"]) / 2, 1
        )

    if hallazgos_similitud is not None:
        indicadores["similitud"] = 1 if hallazgos_similitud else 0

    puntos = 0
    peso_evaluado = 0
    faltantes = []

    for nombre, valor in indicadores.items():
        if valor is None:
            faltantes.append(nombre)
        else:
            puntos += valor * PESOS[nombre]
            peso_evaluado += PESOS[nombre]

    puntuacion = None
    if peso_evaluado > 0:
        puntuacion_calculada = round(1 + (puntos / peso_evaluado) * 4, 2)

        # Evitar una calificación de riesgo mínimo cuando faltan datos.
        if faltantes and puntuacion_calculada < 2.5:
            puntuacion = 2.5
        else:
            puntuacion = puntuacion_calculada

    if es_phishing_pt:
        puntuacion = 5.0

    return {
        "puntuacion": puntuacion,
        "es_dominio_invalido": False,
        "evaluacion_completa": not faltantes,
        "cobertura_porcentaje": peso_evaluado,
        "indicadores": indicadores,
        "indicadores_faltantes": faltantes,
    }