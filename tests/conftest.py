"""Importar los módulos reales sin modificar la estructura existente."""
import sys
import socket
from pathlib import Path
import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "app" / "evaluador-worker"))


@pytest.fixture(autouse=True)
def bloquear_red_real(monkeypatch):
    """Cada prueba debe simular explícitamente sus dependencias externas."""
    def bloquear(*args, **kwargs):
        raise AssertionError("La suite no permite conexiones de red reales")
    async def bloquear_http(*args, **kwargs):
        bloquear()
    monkeypatch.setattr(socket, "create_connection", bloquear)
    monkeypatch.setattr(socket, "gethostbyname", bloquear)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", bloquear_http)
