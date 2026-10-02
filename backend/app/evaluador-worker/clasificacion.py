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
    ssl = obtener_datos("ssl")
    whois = obtener_datos("whois")

    # None significa que falta información para evaluar el indicador.
    indicadores = {
        "reputacion": None,
        "antiguedad": None,
        "ssl": None,
        "similitud": None,
    }

    # 1 = riesgo según la regla; 0 = sin hallazgo según la regla.
    if vt.get("maliciosos", 0) > 0 or google.get("es_maliciosa") is True:
        indicadores["reputacion"] = 1
    elif (
        vt.get("es_conocida") is True
        and vt.get("maliciosos") == 0
        and google.get("es_maliciosa") is False
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

    # Ajustar a una escala de 0 a 100 usando los indicadores disponibles.
    puntuacion = None
    if peso_evaluado > 0:
        puntuacion = round(1 + (puntos / peso_evaluado) * 4, 2)

    return {
        "puntuacion": puntuacion,
        "evaluacion_completa": not faltantes,
        "cobertura_porcentaje": peso_evaluado,
        "indicadores": indicadores,
        "indicadores_faltantes": faltantes,
    }