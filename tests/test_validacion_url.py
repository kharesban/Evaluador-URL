import socket

import pytest

from app.validador import analisisUrl as modulo


def test_estructura_normal_no_genera_alertas():
    resultado = modulo.extraer_metricas_lexicas("https://example.com/")
    assert resultado["banderas_alerta"] == []
    assert resultado["cantidad_subdominios"] == 0
    assert resultado["es_ip_directa"] is False


@pytest.mark.parametrize("url,fragmento", [
    ("https://example.com/" + "a" * 80, "larga"),
    ("https://a.b.c.example.com/", "subdominios"),
    ("https://example.com/?a=1&b=2&c=3&d=4", "símbolos"),
    ("http://192.0.2.1/", "IP directa"),
])
def test_alertas_lexicas(url, fragmento):
    resultado = modulo.extraer_metricas_lexicas(url)
    assert any(fragmento in alerta for alerta in resultado["banderas_alerta"])


@pytest.mark.parametrize("longitud,hay_alerta", [(75, False), (76, True)])
def test_limite_de_longitud(longitud, hay_alerta):
    base = "https://example.com/"
    resultado = modulo.extraer_metricas_lexicas(base + "a" * (longitud - len(base)))
    assert any("larga" in a for a in resultado["banderas_alerta"]) is hay_alerta


def test_normaliza_espacios_y_agrega_https_con_dns_simulado(monkeypatch):
    consultas = []
    def resolver(dominio):
        consultas.append(dominio)
        return "192.0.2.10"
    monkeypatch.setattr(modulo.socket, "gethostbyname", resolver)
    valido, url, metricas, error = modulo.normalizacion_analisis_url("  example.com  ")
    assert valido is True
    assert url == "https://example.com/"
    assert metricas["banderas_alerta"] == []
    assert error is None
    assert consultas == ["example.com"]


def test_dns_fallido_se_reporta_sin_consultar_internet(monkeypatch):
    def resolver(_):
        raise socket.gaierror("NXDOMAIN simulado")
    monkeypatch.setattr(modulo.socket, "gethostbyname", resolver)
    valido, url, metricas, error = modulo.normalizacion_analisis_url("https://example.invalid")
    assert valido is False
    assert url is None and metricas is None
    assert "DNS" in error


@pytest.mark.parametrize("entrada", ["localhost", "https://", "https://exa mple.com"])
def test_entrada_invalida_se_rechaza_antes_de_dns(monkeypatch, entrada):
    def resolver(_):
        pytest.fail("No se debe consultar DNS para una entrada inválida")
    monkeypatch.setattr(modulo.socket, "gethostbyname", resolver)
    valido, url, metricas, error = modulo.normalizacion_analisis_url(entrada)
    assert valido is False
    assert url is None and metricas is None
    assert error
