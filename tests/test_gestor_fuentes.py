import asyncio
from types import SimpleNamespace

import pytest
from app import gestor_fuentes as gestor


def ejecutar(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize('datos,estado', [
    ({'valido': True}, 'ok'),
    ({'estado': 'ok', 'datos': {'valido': True}}, 'ok'),
    ({'estado': 'error', 'datos': None}, 'error'),
    ({'error': 'fallo de fuente'}, 'error'),
    (['respuesta no válida'], 'error'),
])
def test_fuente_normaliza_respuestas_sin_alterar_su_significado(monkeypatch, datos, estado):
    async def consulta(arg):
        assert arg == 'example.com'
        return datos
    monkeypatch.setattr(gestor.importlib, 'import_module', lambda _: SimpleNamespace(consulta=consulta))
    r = ejecutar(gestor._ejecutar_fuente_async('modulo', 'consulta', 'example.com', 'ssl'))
    assert r['estado'] == estado
    assert r['tiempo_ejecucion_seg'] >= 0


def test_fuente_sincrona_se_ejecuta_y_normaliza(monkeypatch):
    monkeypatch.setattr(gestor.importlib, 'import_module', lambda _: SimpleNamespace(consulta=lambda _: {'valido': False}))
    r = ejecutar(gestor._ejecutar_fuente_async('modulo', 'consulta', 'example.com', 'ssl'))
    assert r['datos']['valido'] is False


def test_fuente_timeout_se_distingue_de_un_resultado_limpio(monkeypatch):
    async def consulta(_):
        raise asyncio.TimeoutError()
    monkeypatch.setattr(gestor.importlib, 'import_module', lambda _: SimpleNamespace(consulta=consulta))
    assert ejecutar(gestor._ejecutar_fuente_async('m', 'consulta', 'x', 'ssl'))['estado'] == 'timeout'


def test_fuente_excepcion_se_convierte_en_error_controlado(monkeypatch):
    def importar(_):
        raise ImportError('fallo')
    monkeypatch.setattr(gestor.importlib, 'import_module', importar)
    r = ejecutar(gestor._ejecutar_fuente_async('m', 'consulta', 'x', 'ssl'))
    assert r['estado'] == 'error'
    assert r['error'] == 'ImportError'


@pytest.mark.parametrize('cantidad,estado', [(0, 'sin_resultados'), (2, 'parcial'), (5, 'completo')])
def test_gestor_consolida_fuentes_disponibles(monkeypatch, cantidad, estado):
    consultas = []
    async def fuente(mod, func, arg, nombre):
        consultas.append((nombre, arg))
        return {'estado': 'ok' if len(consultas) <= cantidad else 'timeout', 'datos': {}, 'tiempo_ejecucion_seg': .01}
    monkeypatch.setattr(gestor, '_ejecutar_fuente_async', fuente)
    r = ejecutar(gestor.analizar_fuentes(' example.com '))
    assert r['estado'] == estado
    assert set(r['fuentes']) == {'virustotal', 'safe_browsing', 'phishtank', 'ssl', 'whois'}
    assert dict(consultas)['ssl'] == 'example.com'
    assert dict(consultas)['virustotal'] == 'https://example.com'


def test_gestor_una_excepcion_no_descarta_el_resto(monkeypatch):
    async def fuente(mod, func, arg, nombre):
        if nombre == 'whois':
            raise RuntimeError('sin whois')
        return {'estado': 'ok', 'datos': {}, 'tiempo_ejecucion_seg': 11}
    monkeypatch.setattr(gestor, '_ejecutar_fuente_async', fuente)
    r = ejecutar(gestor.analizar_fuentes('https://example.com'))
    assert r['estado'] == 'parcial'
    assert r['fuentes']['whois']['estado'] == 'error'
    assert len(r['fuentes']) == 5


def test_gestor_rechaza_url_sin_dominio():
    with pytest.raises(ValueError):
        ejecutar(gestor.analizar_fuentes('https://'))
