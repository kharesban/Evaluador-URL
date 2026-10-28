import asyncio
from unittest.mock import AsyncMock

import pytest
import worker


@pytest.fixture
def entorno_worker(monkeypatch):
    monkeypatch.setattr(worker, 'load_dotenv', lambda *a, **kw: None)
    monkeypatch.setattr(worker, 'normalizacion_analisis_url', lambda _: (True, 'https://example.com/', {}, None))
    monkeypatch.setattr(worker, 'analizar_similitud', lambda _: [])
    fuentes = {
        'virustotal': {'estado': 'ok', 'datos': {'maliciosos': 0, 'es_conocida': True}},
        'safe_browsing': {'estado': 'ok', 'datos': {'es_maliciosa': False}},
        'phishtank': {'estado': 'ok', 'datos': {'es_phishing': False}},
        'ssl': {'estado': 'ok', 'datos': {'valido': True}},
        'whois': {'estado': 'ok', 'datos': {'dias_antiguedad': 1000}},
    }
    mock = AsyncMock(return_value={'estado': 'completo', 'fuentes': fuentes})
    monkeypatch.setattr(worker, 'analizar_fuentes', mock)
    return mock


def test_worker_integra_validacion_fuentes_similitud_y_calculo_real(entorno_worker):
    r = asyncio.run(worker.procesar_analisis('example.com'))
    assert r['riesgo']['puntuacion'] == 1
    assert r['riesgo']['evaluacion_completa'] is True
    assert r['hallazgos_similitud'] == []
    assert r['tiempo_ejecucion_total_seg'] >= 0
    entorno_worker.assert_awaited_once_with('https://example.com/')


def test_worker_sintaxis_tld_invalida_se_rechaza_antes_de_fuentes(monkeypatch, entorno_worker):
    monkeypatch.setattr(worker, 'normalizacion_analisis_url', lambda _: (False, None, None, 'TLD inválido'))
    with pytest.raises(ValueError, match='TLD'):
        asyncio.run(worker.procesar_analisis('localhost'))
    entorno_worker.assert_not_awaited()


@pytest.mark.parametrize('url', ['example.invalid', 'https://example.invalid'])
def test_worker_dns_invalido_no_recibe_puntuacion(monkeypatch, entorno_worker, url):
    monkeypatch.setattr(worker, 'normalizacion_analisis_url', lambda _: (False, None, None, 'DNS'))
    r = asyncio.run(worker.procesar_analisis(url))
    assert r['riesgo']['es_dominio_invalido'] is True
    assert r['riesgo']['puntuacion'] is None


def test_worker_fallo_similitud_conserva_el_resto_sin_inventar_datos(monkeypatch, entorno_worker):
    def similitud(_):
        raise RuntimeError('falló')
    monkeypatch.setattr(worker, 'analizar_similitud', similitud)
    r = asyncio.run(worker.procesar_analisis('example.com'))
    assert r['hallazgos_similitud'] is None
    assert 'similitud' in r['riesgo']['indicadores_faltantes']


def test_worker_registra_incumplimiento_de_tiempos_controlados(monkeypatch, entorno_worker, caplog):
    entorno_worker.return_value['fuentes']['ssl']['tiempo_seg'] = 11
    ticks = iter([0, 0, 0, 0, 0, 25])
    monkeypatch.setattr(worker.time, 'perf_counter', lambda: next(ticks))
    with caplog.at_level('INFO', logger='servidor_logger'):
        r = asyncio.run(worker.procesar_analisis('example.com'))
    assert r['tiempo_ejecucion_total_seg'] == 25
    assert 'INCUMPLE' in caplog.text


def test_worker_propagacion_de_error_inesperado_hasta_capa_api(entorno_worker):
    entorno_worker.side_effect = RuntimeError('fuentes fallaron')
    with pytest.raises(RuntimeError):
        asyncio.run(worker.procesar_analisis('example.com'))
