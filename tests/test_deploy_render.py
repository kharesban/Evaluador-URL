"""El CD no debe aprobar un servicio que aún esté publicando otro commit."""
import importlib.util
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

import pytest


spec = importlib.util.spec_from_file_location("deploy_render", Path(__file__).parents[1] / ".github/scripts/deploy_render.py")
cd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cd)
COMMIT = "a" * 40


def test_hook_solicita_el_commit_exacto_sin_reutilizar_ref_anterior(monkeypatch):
    respuesta = BytesIO(b'{}')
    respuesta.status = 200
    abrir = Mock(return_value=respuesta)
    monkeypatch.setattr(cd, 'urlopen', abrir)
    cd.solicitar_despliegue('https://api.render.com/deploy/srv-prueba?key=secreto&ref=viejo', COMMIT)
    solicitud = abrir.call_args.args[0]
    assert solicitud.method == 'POST'
    assert parse_qs(urlsplit(solicitud.full_url).query) == {'key': ['secreto'], 'ref': [COMMIT]}


def test_no_aprueba_la_version_anterior_y_espera_la_correcta(monkeypatch):
    leer = Mock(side_effect=[{'commit': 'viejo', 'status': 'ok'}, {'commit': COMMIT, 'status': 'ok'}])
    monkeypatch.setattr(cd, 'leer_json', leer)
    pausa = Mock()
    monkeypatch.setattr(cd.time, 'sleep', pausa)
    cd.esperar_version('https://backend.onrender.com', '/health', COMMIT, 'backend')
    assert leer.call_count == 2
    pausa.assert_called_once_with(10)


def test_no_aprueba_un_backend_en_estado_incorrecto(monkeypatch):
    monkeypatch.setattr(cd, 'leer_json', Mock(return_value={'commit': COMMIT, 'status': 'error'}))
    monkeypatch.setattr(cd.time, 'monotonic', Mock(side_effect=[0, 0, 2]))
    monkeypatch.setattr(cd.time, 'sleep', Mock())
    with pytest.raises(TimeoutError):
        cd.esperar_version('https://backend.onrender.com', '/health', COMMIT, 'backend', 1)


def test_fallo_de_hook_no_filtra_credenciales_y_guarda_reporte(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    for clave, valor in {
        'GITHUB_SHA': COMMIT,
        'RENDER_BACKEND_URL': 'https://backend.onrender.com',
        'RENDER_FRONTEND_URL': 'https://frontend.onrender.com',
        'RENDER_BACKEND_DEPLOY_HOOK': 'https://api.render.com/deploy/srv-b?key=MUY_SECRETO',
        'RENDER_FRONTEND_DEPLOY_HOOK': 'https://api.render.com/deploy/srv-f?key=OTRO_SECRETO',
    }.items():
        monkeypatch.setenv(clave, valor)
    monkeypatch.setattr(cd, 'solicitar_despliegue', Mock(side_effect=RuntimeError('MUY_SECRETO')))
    assert cd.main() == 1
    assert 'MUY_SECRETO' not in capsys.readouterr().err
    assert '"estado": "error"' in (tmp_path / 'qa-results/deploy.json').read_text()
