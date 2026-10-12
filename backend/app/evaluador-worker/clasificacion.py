PESOS = {
    "reputacion": 40,
    "antiguedad": 20,
    "ssl": 15,
    "similitud": 25,
}


def calcular_riesgo(fuentes, hallazgos_similitud):
    # Solo utilizar datos de consultas que terminaron correctamente.
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

    # None significa que falta información para evaluar el indicador.
    indicadores = {
        "reputacion": None,
        "antiguedad": None,
        "ssl": None,
        "similitud": None,
    }

    # REPUTACIÓN (VirusTotal + Google Safe Browsing + PhishTank)
    # Se considera phishing si PhishTank lo marca activo o si está registrado en su base de datos histórica
    es_phishing_pt = (
        phishtank.get("es_phishing") is True 
        or phishtank.get("en_base_datos") is True
    )
    es_malicioso_vt = vt.get("maliciosos", 0) > 0
    es_malicioso_gsb = google.get("es_maliciosa") is True

    # 1 = Riesgo máximo detectado
    if es_phishing_pt or es_malicioso_vt or es_malicioso_gsb:
        indicadores["reputacion"] = 1
    # 0 = Sin hallazgos y evaluado
    elif (
        vt.get("es_conocida") is True
        and vt.get("maliciosos") == 0
        and google.get("es_maliciosa") is False
        and phishtank.get("es_phishing") is False
        and phishtank.get("en_base_datos") is False
    ):
        indicadores["reputacion"] = 0

    # ANTIGUEDAD CON WHOIS
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

    # SIMILITUD (TYPOSQUATTING)
    if hallazgos_similitud is not None:
        indicadores["similitud"] = 1 if hallazgos_similitud else 0

    # CALCULO
    puntos = 0
    peso_evaluado = 0
    faltantes = []

    for nombre, valor in indicadores.items():
        if valor is None:
            faltantes.append(nombre)
        else:
            puntos += valor * PESOS[nombre]
            peso_evaluado += PESOS[nombre]

    # Ajustar a una escala de 1 a 5 usando los indicadores disponibles.
    puntuacion = None
    if peso_evaluado > 0:
        puntuacion = round(1 + (puntos / peso_evaluado) * 4, 2)

    # REGLA PARA PHISHTANK (Override de riesgo crítico)
    if es_phishing_pt:
        puntuacion = 5.0

    return {
        "puntuacion": puntuacion,
        "evaluacion_completa": not faltantes,
        "cobertura_porcentaje": peso_evaluado,
        "indicadores": indicadores,
        "indicadores_faltantes": faltantes,
    }