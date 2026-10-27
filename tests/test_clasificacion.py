from copy import deepcopy

import pytest

from clasificacion import calcular_riesgo


@pytest.fixture
def fuentes_limpias():
    return {
        "virustotal": {"estado": "ok", "datos": {"es_conocida": True, "maliciosos": 0}},
        "safe_browsing": {"estado": "ok", "datos": {"es_maliciosa": False}},
        "phishtank": {"estado": "ok", "datos": {"es_phishing": False}},
        "ssl": {"estado": "ok", "datos": {"valido": True}},
        "whois": {"estado": "ok", "datos": {"dias_antiguedad": 1000}},
    }


def test_sitio_sin_alertas_tiene_riesgo_minimo(fuentes_limpias):
    resultado = calcular_riesgo(fuentes_limpias, [])
    assert resultado["puntuacion"] == 1
    assert resultado["evaluacion_completa"] is True
    assert resultado["cobertura_porcentaje"] == 100
    assert resultado["indicadores_faltantes"] == []


def test_todos_los_indicadores_de_riesgo_dan_puntaje_maximo(fuentes_limpias):
    fuentes_limpias["virustotal"]["datos"]["maliciosos"] = 3
    fuentes_limpias["ssl"]["datos"]["valido"] = False
    fuentes_limpias["whois"]["datos"]["dias_antiguedad"] = 10
    resultado = calcular_riesgo(fuentes_limpias, [{"dominio": "g00gle.test", "referencia": "google.com", "similitud": 66.67}])
    assert resultado["puntuacion"] == 5
    assert resultado["indicadores"] == dict.fromkeys(["reputacion", "antiguedad", "ssl", "similitud"], 1)


@pytest.mark.parametrize("fuente,campo,valor", [
    ("virustotal", "maliciosos", 1),
    ("safe_browsing", "es_maliciosa", True),
    ("phishtank", "es_phishing", True),
])
def test_una_fuente_positiva_aporta_el_peso_de_reputacion(fuentes_limpias, fuente, campo, valor):
    fuentes_limpias[fuente]["datos"][campo] = valor
    resultado = calcular_riesgo(fuentes_limpias, [])
    assert resultado["puntuacion"] == 2.6
    assert resultado["phishing_confirmado"] is (fuente == "phishtank")
    assert "riesgo" in resultado["detalle_indicadores"][0]["explicacion"]


@pytest.mark.parametrize("dias,esperado", [(0, 1), (29, 1), (30, 1), (180, 550/700), (380, .5), (729, 1/700), (730, 0), (1000, 0)])
def test_limites_de_antiguedad(fuentes_limpias, dias, esperado):
    fuentes_limpias["whois"]["datos"]["dias_antiguedad"] = dias
    resultado = calcular_riesgo(fuentes_limpias, [])
    assert resultado["indicadores"]["antiguedad"] == pytest.approx(esperado)
    assert resultado["puntuacion"] == round(1 + .8 * esperado, 3)


@pytest.mark.parametrize("dias", [180, 380, 729])
def test_explicacion_de_antiguedad_es_coherente_con_riesgo_intermedio(fuentes_limpias, dias):
    fuentes_limpias["whois"]["datos"]["dias_antiguedad"] = dias
    resultado = calcular_riesgo(fuentes_limpias, [])
    explicacion = resultado["detalle_indicadores"][1]["explicacion"]
    assert "730" in explicacion
    assert "no suma riesgo" not in explicacion


@pytest.mark.parametrize("dias", [-1, None, "desconocida"])
def test_antiguedad_no_disponible_no_se_inventa(fuentes_limpias, dias):
    fuentes_limpias["whois"]["datos"]["dias_antiguedad"] = dias
    resultado = calcular_riesgo(fuentes_limpias, [])
    assert resultado["indicadores"]["antiguedad"] is None
    assert "antiguedad" in resultado["indicadores_faltantes"]
    assert resultado["cobertura_porcentaje"] == 80


def test_dominio_no_resuelto_no_recibe_calificacion(fuentes_limpias):
    resultado = calcular_riesgo(fuentes_limpias, [], {"dns_resuelto": False})
    assert resultado["puntuacion"] is None
    assert resultado["es_dominio_invalido"] is True
    assert resultado["evaluacion_completa"] is False


def test_sin_datos_no_se_presenta_como_sitio_seguro():
    resultado = calcular_riesgo({}, None)
    assert resultado["puntuacion"] is None
    assert resultado["cobertura_porcentaje"] == 0
    assert len(resultado["indicadores_faltantes"]) == 4
    assert all(d["estado"] == "sin_datos" for d in resultado["detalle_indicadores"])


def test_fuente_fallida_no_aporta_datos_positivos(fuentes_limpias):
    fuentes_limpias["virustotal"] = {"estado": "error", "datos": {"maliciosos": 99}}
    resultado = calcular_riesgo(fuentes_limpias, [])
    assert resultado["indicadores"]["reputacion"] is None
    assert resultado["evaluacion_completa"] is False
    assert resultado["cobertura_porcentaje"] == 60


def test_explicacion_ssl_invalido_refleja_su_peso(fuentes_limpias):
    fuentes_limpias["ssl"]["datos"]["valido"] = False
    resultado = calcular_riesgo(fuentes_limpias, [])
    detalle = next(d for d in resultado["detalle_indicadores"] if d["clave"] == "ssl")
    assert resultado["puntuacion"] == 1.6
    assert detalle["contribucion_ponderada"] == 15
    assert "no es válido" in detalle["explicacion"]


def test_calculo_no_modifica_las_fuentes(fuentes_limpias):
    original = deepcopy(fuentes_limpias)
    calcular_riesgo(fuentes_limpias, [])
    assert fuentes_limpias == original
