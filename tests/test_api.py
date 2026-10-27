import logging
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
import servidor


@pytest.fixture
def cliente(monkeypatch):
    servidor.tareas.clear()
    servidor.LOG_BUFFER.clear()
    monkeypatch.setattr(servidor, "procesar_analisis", AsyncMock(return_value={"riesgo": {"puntuacion": 1}}))
    with TestClient(servidor.app) as client:
        yield client
    servidor.tareas.clear()
    servidor.LOG_BUFFER.clear()


def test_api_crea_tarea_202_y_permite_consultar_resultado(cliente):
    r = cliente.post('/analizar', json={"url": "https://example.com"})
    assert r.status_code == 202
    tarea = r.json()
    assert tarea['estado'] == 'en_proceso'
    assert tarea['id']
    consulta = cliente.get('/tareas/' + tarea['id'])
    assert consulta.status_code == 200
    assert consulta.json()['estado'] == 'completado'
    assert consulta.json()['resultado']['riesgo']['puntuacion'] == 1
    servidor.procesar_analisis.assert_awaited_once_with('https://example.com/')


@pytest.mark.parametrize('cuerpo', [{}, {'url': ''}, {'url': 'no es url'}, {'url': 'ftp://example.com'}])
def test_api_rechaza_solicitudes_invalidas_sin_iniciar_worker(cliente, cuerpo):
    assert cliente.post('/analizar', json=cuerpo).status_code == 422
    servidor.procesar_analisis.assert_not_awaited()


def test_api_tarea_inexistente_devuelve_404(cliente):
    assert cliente.get('/tareas/no-existe').status_code == 404


def test_api_fallo_worker_se_consulta_como_error_sin_exponer_excepcion(cliente):
    servidor.procesar_analisis.side_effect = RuntimeError('detalle interno sensible')
    tarea = cliente.post('/analizar', json={'url': 'https://example.com'}).json()
    datos = cliente.get('/tareas/' + tarea['id']).json()
    assert datos['estado'] == 'error'
    assert datos['mensaje'] == 'No fue posible completar el análisis.'
    assert 'detalle interno' not in datos['mensaje']


def test_api_registros_limitados_a_200_y_totales_coherentes(cliente):
    for i in range(205):
        record = logging.LogRecord('prueba', logging.INFO, '', 0, 'evento %s', (i,), None)
        servidor.memory_handler.emit(record)
    r = cliente.get('/logs')
    assert r.status_code == 200
    assert r.json()['total_registros'] == 200
    assert len(r.json()['logs']) == 200
    assert 'evento 204' in r.json()['logs'][-1]


def test_api_publica_su_contrato(cliente):
    assert {'/analizar', '/tareas/{tarea_id}', '/logs'} <= set(cliente.get('/openapi.json').json()['paths'])
