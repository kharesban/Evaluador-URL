PESOS = {
    "reputacion": 40,
    "antiguedad": 20,
    "ssl": 15,
    "similitud": 25,
}


def calcular_riesgo(fuentes, hallazgos_similitud, metricas_lexicas=None):
    # 0. VALIDACIÓN DNS: Si el dominio no resuelve, no se otorga puntuación numérica
    if metricas_lexicas and metricas_lexicas.get("dns_resuelto") is False:
        return {
            "puntuacion": None,
            "es_dominio_invalido": True,
            "mensaje": "La página no está registrada como un dominio válido o activo.",
            "evaluacion_completa": False,
            "cobertura_porcentaje": 0,
            "indicadores": {},
            "indicadores_faltantes": ["reputacion", "antiguedad", "ssl", "similitud"],
        }

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

    indicadores = {
        "reputacion": None,
        "antiguedad": None,
        "ssl": None,
        "similitud": None,
    }

    # 1. REPUTACIÓN (VirusTotal + Google Safe Browsing + PhishTank)
    # Únicamente se considera si PhishTank confirmó que ES phishing (valid == True)
    es_phishing_pt = phishtank.get("es_phishing") is True
    es_malicioso_vt = vt.get("maliciosos", 0) > 0
    es_malicioso_gsb = google.get("es_maliciosa") is True

    # 1 = Riesgo máximo detectado
    if es_phishing_pt or es_malicioso_vt or es_malicioso_gsb:
        indicadores["reputacion"] = 1
    # 0 = Sin hallazgos y evaluado correctamente
    elif (
        vt.get("es_conocida") is True
        and vt.get("maliciosos") == 0
        and google.get("es_maliciosa") is False
        and phishtank.get("es_phishing") is False
    ):
        indicadores["reputacion"] = 0

    # 2. ANTIGÜEDAD CON WHOIS
    dias = whois.get("dias_antiguedad")
    if isinstance(dias, (int, float)) and dias >= 0:
        if dias < 30:
            indicadores["antiguedad"] = 1
        elif dias < 180:
            indicadores["antiguedad"] = 0.5
        else:
            indicadores["antiguedad"] = 0

    # 3. ESTADO SSL
    if ssl.get("valido") is True:
        indicadores["ssl"] = 0
    elif ssl.get("valido") is False:
        indicadores["ssl"] = 1

    # 4. SIMILITUD (TYPOSQUATTING)
    if hallazgos_similitud is not None:
        indicadores["similitud"] = 1 if hallazgos_similitud else 0

    # CÁLCULO
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

        # AJUSTE LÓGICO DE SEGURIDAD:
        # Si faltan datos en indicadores (WHOIS/SSL) y el cálculo daría 1.0 (Limpio por omisión),
        # se ajusta a un piso mínimo de 2.5/5.0 para evitar dar una calificación de "completamente seguro" a ciegas.
        if faltantes and puntuacion_calculada < 2.5:
            puntuacion = 2.5
        else:
            puntuacion = puntuacion_calculada

    # REGLA CRÍTICA PARA PHISHTANK (Override directo a riesgo máximo)
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