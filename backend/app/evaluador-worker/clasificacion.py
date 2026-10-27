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
        elif dias < 730:
            indicadores["antiguedad"] = (730 - dias) / 700
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
        puntuacion = round(
            1 + 4 * puntos / sum(PESOS.values()),
            3
        )

    # HU-17: explicar cómo influyó cada indicador en el resultado.
    fuentes_reputacion = []
    if es_phishing_pt:
        fuentes_reputacion.append("PhishTank confirmó que la URL es phishing")
    if es_malicioso_vt:
        fuentes_reputacion.append(f"VirusTotal reportó {vt.get('maliciosos')} detecciones maliciosas")
    if es_malicioso_gsb:
        fuentes_reputacion.append("Google Safe Browsing marcó la URL como maliciosa")
    if indicadores["reputacion"] == 1:
        explicacion_reputacion = "Se detectó una señal de riesgo: " + "; ".join(fuentes_reputacion) + "."
    elif indicadores["reputacion"] == 0:
        explicacion_reputacion = "Las tres fuentes respondieron y no reportaron phishing ni detecciones maliciosas."
    else:
        explicacion_reputacion = "No hay confirmación suficiente de todas las fuentes para clasificar la reputación."

    if indicadores["antiguedad"] is None:
        explicacion_antiguedad = "No fue posible obtener una antigüedad válida mediante WHOIS."
    elif dias < 30:
        explicacion_antiguedad = f"El dominio tiene {dias} días. Los dominios de menos de 30 días reciben riesgo alto en este indicador."
    elif dias < 730:
        explicacion_antiguedad = f"El dominio tiene {dias} días. Entre 30 y 729 días, el riesgo por antigüedad disminuye gradualmente hasta llegar a cero a los 730 días."
    else:
        explicacion_antiguedad = f"El dominio tiene {dias} días. Tiene al menos 730 días y no suma riesgo por antigüedad."

    if indicadores["ssl"] == 1:
        explicacion_ssl = "El certificado SSL/TLS no es válido según la consulta; esto añade riesgo."
    elif indicadores["ssl"] == 0:
        explicacion_ssl = "El certificado SSL/TLS aparece como válido; este indicador no añade riesgo."
    else:
        explicacion_ssl = "No fue posible confirmar el estado del certificado SSL/TLS."

    if indicadores["similitud"] == 1:
        parecidos = ", ".join(f"{h.get('dominio', 'dominio desconocido')} se parece a {h.get('referencia', 'un dominio conocido')} ({h.get('similitud', 'N/D')}%)" for h in (hallazgos_similitud or []))
        explicacion_similitud = "Se detectaron posibles similitudes sospechosas: " + parecidos + "."
    elif indicadores["similitud"] == 0:
        explicacion_similitud = "No se encontraron similitudes sospechosas con los dominios oficiales configurados."
    else:
        explicacion_similitud = "No fue posible completar el análisis de similitud del dominio."

    descripciones = [
        ("reputacion", "Reputación externa", explicacion_reputacion),
        ("antiguedad", "Antigüedad del dominio (WHOIS)", explicacion_antiguedad),
        ("ssl", "Certificado SSL/TLS", explicacion_ssl),
        ("similitud", "Similitud del dominio", explicacion_similitud),
    ]
    detalles = []
    for clave, nombre, explicacion in descripciones:
        valor = indicadores[clave]
        impacto = ("Alto" if valor == 1 else "Medio" if valor == 0.5 else "Bajo") if valor is not None else None
        detalles.append({
            "clave": clave,
            "indicador": nombre,
            "peso": PESOS[clave],
            "valor": valor,
            "impacto": impacto,
            "estado": "evaluado" if valor is not None else "sin_datos",
            "explicacion": explicacion,
            "contribucion_ponderada": round(valor * PESOS[clave], 2) if valor is not None else None,
        })

    return {
        "puntuacion": puntuacion,
        "phishing_confirmado": es_phishing_pt,
        "es_dominio_invalido": False,
        "evaluacion_completa": not faltantes,
        "cobertura_porcentaje": peso_evaluado,
        "indicadores": indicadores,
        "indicadores_faltantes": faltantes,
        "detalle_indicadores": detalles,
    }

