import logging
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
import servidor
from app.db import database


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    # Probar la persistencia real sin tocar evaluaciones.db del desarrollador.
    ruta = str(tmp_path / 'evaluaciones_prueba.db')
    monkeypatch.setattr(database, 'DB_PATH', ruta)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    servidor.LOG_BUFFER.clear()
    monkeypatch.setattr(servidor, "procesar_analisis", AsyncMock(return_value={"riesgo": {"puntuacion": 1}}))
    with TestClient(servidor.app) as client:
        yield client
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
    historial = cliente.get("/tareas")
    assert historial.status_code == 200
    assert historial.json()["total"] == 1
    assert historial.json()["items"][0]["id"] == tarea["id"]
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
    assert {'/analizar', '/tareas', '/tareas/{tarea_id}', '/logs'} <= set(cliente.get('/openapi.json').json()['paths'])


def test_salud_informa_el_commit_sin_ejecutar_analisis(cliente, monkeypatch):
    monkeypatch.setenv('RENDER_GIT_COMMIT', 'a' * 40)
    assert cliente.get('/health').json() == {'status': 'ok', 'commit': 'a' * 40}
    servidor.procesar_analisis.assert_not_awaited()


@pytest.mark.parametrize('valor,extras', [
    ('', []),
    ('https://frontend.onrender.com/', ['https://frontend.onrender.com']),
    (' https://uno.onrender.com, ,https://dos.onrender.com ', ['https://uno.onrender.com', 'https://dos.onrender.com']),
])
def test_configuracion_cors_conserva_local_y_admite_origenes_publicados(monkeypatch, valor, extras):
    monkeypatch.setenv('CORS_ORIGINS', valor)
    assert servidor.origenes_permitidos() == ['http://localhost:5173', 'http://127.0.0.1:5173'] + extras


def test_historial_compartido_sobrevive_al_reinicio_y_a_48_horas(monkeypatch, tmp_path):
    import sqlite3
    ruta = str(tmp_path / 'historial.db')
    monkeypatch.setattr(database, 'DB_PATH', ruta)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv('ENABLE_TASK_CLEANUP', raising=False)
    analisis = AsyncMock(return_value={'riesgo': {'puntuacion': 2}})
    monkeypatch.setattr(servidor, 'procesar_analisis', analisis)
    with TestClient(servidor.app) as client:
        tarea = client.post('/analizar', json={'url': 'https://example.org'}).json()['id']
    db = sqlite3.connect(ruta)
    try:
        db.execute("UPDATE tareas SET fecha_creacion = datetime('now', '-2 days') WHERE id = ?", (tarea,))
        db.commit()
    finally:
        db.close()
    with TestClient(servidor.app) as client:
        reporte = client.get('/tareas/' + tarea).json()
        assert reporte['url'] == 'https://example.org/'
        assert reporte['id'] == tarea
        assert reporte['resultado']['riesgo']['puntuacion'] == 2
    analisis.assert_awaited_once()


def test_api_historial_compartido_admite_paginacion_sin_autenticacion(cliente):
    for dominio in ("uno.example", "dos.example", "tres.example"):
        respuesta = cliente.post("/analizar", json={"url": f"https://{dominio}"})
        assert respuesta.status_code == 202

    primera = cliente.get("/tareas?limit=2&offset=0")
    segunda = cliente.get("/tareas?limit=2&offset=2")
    assert primera.status_code == 200
    assert segunda.status_code == 200
    assert primera.json()["total"] == 3
    assert len(primera.json()["items"]) == 2
    assert len(segunda.json()["items"]) == 1
    assert all(item["resultado"] for item in primera.json()["items"])


def test_limpieza_en_servidor_solo_se_activa_con_opt_in(monkeypatch, tmp_path):
    import asyncio
    import threading

    ruta = str(tmp_path / "limpieza_opt_in.db")
    monkeypatch.setattr(database, "DB_PATH", ruta)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("ENABLE_TASK_CLEANUP", "1")
    iniciada = threading.Event()

    async def limpieza_falsa(intervalo_segundos=3600):
        iniciada.set()
        await asyncio.Future()

    monkeypatch.setattr(servidor, "tarea_limpieza_24h", limpieza_falsa)
    with TestClient(servidor.app) as client:
        assert client.get("/health").status_code == 200
        assert iniciada.wait(timeout=2)
