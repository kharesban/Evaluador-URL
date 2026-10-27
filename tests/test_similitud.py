import pytest

from app.validador.similitud_dominio import analizar_similitud


@pytest.mark.parametrize("url", ["https://google.com", "https://accounts.google.com", "  WWW.GOOGLE.COM  ", "https://nu.com.co", "https://example.org"])
def test_dominios_oficiales_y_sin_coincidencias_no_alertan(url):
    assert analizar_similitud(url) == []


@pytest.mark.parametrize("url,referencia", [
    ("https://goggle.com", "google.com"),
    ("https://googel.com", "google.com"),
    ("https://google-login.example", "google.com"),
    ("https://nu-pagos.example", "nu.com.co"),
    ("https://pagosnu.example", "nu.com.co"),
    ("https://pagos-nu-oficial.example", "nu.com.co"),
])
def test_detecta_variaciones_y_uso_de_marca(url, referencia):
    hallazgos = analizar_similitud(url)
    assert hallazgos
    assert hallazgos[0]["referencia"] == referencia
    assert 0 <= hallazgos[0]["similitud"] <= 100
    assert hallazgos[0]["motivo"]


def test_rechaza_url_sin_dominio():
    with pytest.raises(ValueError, match="dominio"):
        analizar_similitud("https://")
