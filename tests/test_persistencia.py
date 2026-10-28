import asyncio
from unittest.mock import Mock

import aiosqlite
import pytest
from app.db import database, limpieza


@pytest.fixture
def ruta_db(monkeypatch, tmp_path):
    ruta = str(tmp_path / 'persistencia_prueba.db')
    monkeypatch.setattr(database, 'DB_PATH', ruta)
    monkeypatch.setattr(limpieza, 'DB_PATH', ruta)
    return ruta


def test_resultado_persiste_al_cerrar_y_reabrir_la_base(ruta_db):
    async def escenario():
        await database.init_db()
        await database.guardar_tarea_inicial('persistente')
        await database.guardar_tarea_resultado('persistente', 'completado', 1.23456, {'texto': 'Evaluación válida'})
        # Cada operación abre una conexión distinta: no depende de un diccionario.
        tarea = await database.obtener_tarea_por_id('persistente')
        assert tarea == {'id': 'persistente', 'estado': 'completado', 'tiempo_ejecucion_seg': 1.2346, 'resultado': {'texto': 'Evaluación válida'}}
        assert await database.obtener_tarea_por_id('no-existe') is None
    asyncio.run(escenario())


@pytest.mark.parametrize('antigua', [False, True])
def test_limpieza_respeta_las_tareas_recientes_y_purga_las_expiradas(ruta_db, monkeypatch, antigua):
    async def detener(_):
        raise asyncio.CancelledError
    monkeypatch.setattr(limpieza.asyncio, 'sleep', detener)
    async def escenario():
        await database.init_db()
        await database.guardar_tarea_inicial('reciente')
        if antigua:
            await database.guardar_tarea_inicial('expirada')
            async with aiosqlite.connect(ruta_db) as db:
                await db.execute("UPDATE tareas SET fecha_creacion = datetime('now', '-25 hours') WHERE id = 'expirada'")
                await db.commit()
        with pytest.raises(asyncio.CancelledError):
            await limpieza.tarea_limpieza_24h(0)
        assert await database.obtener_tarea_por_id('reciente') is not None
        assert await database.obtener_tarea_por_id('expirada') is None
    asyncio.run(escenario())


def test_limpieza_se_puede_cancelar_sin_ocultar_errores_de_base(monkeypatch):
    def cancelar(*args, **kwargs):
        raise asyncio.CancelledError
    monkeypatch.setattr(limpieza.aiosqlite, 'connect', cancelar)
    asyncio.run(limpieza.tarea_limpieza_24h())


def test_limpieza_registra_un_fallo_y_no_termina_silenciosamente(monkeypatch):
    async def detener(_):
        raise asyncio.CancelledError
    monkeypatch.setattr(limpieza.asyncio, 'sleep', detener)
    monkeypatch.setattr(limpieza.aiosqlite, 'connect', Mock(side_effect=aiosqlite.OperationalError('base no disponible')))
    registrar = Mock()
    monkeypatch.setattr(limpieza.logger, 'error', registrar)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(limpieza.tarea_limpieza_24h())
    assert 'base no disponible' in registrar.call_args.args[0]
