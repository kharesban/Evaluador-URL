import asyncio
import datetime
import socket
import ssl
from unittest.mock import MagicMock

import httpx
import pytest
from app.diagnostico_externo import safeBrowsing_module as google
from app.diagnostico_externo import virusTotal_module as vt
from app.diagnostico_externo import phishTank_module as pt
from app.diagnostico_externo import whois_module as whois
from app.diagnostico_externo import SSL_module as tls


@pytest.fixture
def transporte(monkeypatch):
    original = httpx.AsyncClient
    peticiones = []
    def configurar(respuestas):
        cola = iter(respuestas)
        def handler(request):
            peticiones.append(request)
            siguiente = next(cola)
            if isinstance(siguiente, Exception):
                raise siguiente
            return httpx.Response(siguiente[0], json=siguiente[1], request=request)
        monkeypatch.setattr(httpx, 'AsyncClient', lambda *a, **kw: original(transport=httpx.MockTransport(handler)))
        return peticiones
    return configurar


@pytest.mark.parametrize('modulo,clave,funcion', [(google, 'GOOGLE_KEY', 'consultar_google_safe_browsing'), (vt, 'VIRUSTOTAL_KEY', 'consultar_virustotal')])
def test_reputacion_sin_credencial_se_reporta_como_error(monkeypatch, modulo, clave, funcion):
    monkeypatch.setattr(modulo.settings, clave, '')
    r = asyncio.run(getattr(modulo, funcion)('https://example.com'))
    assert 'no configurada' in r['error']


@pytest.mark.parametrize('datos,maliciosa', [({}, False), ({'matches': [{'threatType': 'MALWARE'}]}, True)])
def test_google_traduce_hallazgos_y_envia_url_correcta(monkeypatch, transporte, datos, maliciosa):
    monkeypatch.setattr(google.settings, 'GOOGLE_KEY', 'clave-de-prueba')
    peticiones = transporte([(200, datos)])
    r = asyncio.run(google.consultar_google_safe_browsing('https://example.com'))
    assert r['es_maliciosa'] is maliciosa
    assert b'https://example.com' in peticiones[0].content


@pytest.mark.parametrize('fallo', [httpx.ReadTimeout('timeout simulado'), (500, {'error': 'fallo remoto'})])
def test_google_fallo_remoto_no_se_presenta_como_limpio(monkeypatch, transporte, fallo):
    monkeypatch.setattr(google.settings, 'GOOGLE_KEY', 'prueba')
    transporte([fallo])
    r = asyncio.run(google.consultar_google_safe_browsing('https://example.com'))
    assert r.get('error')
    assert 'es_maliciosa' not in r


@pytest.mark.parametrize('estado,datos,esperado', [
    (404, {}, False),
    (200, {'data': {'attributes': {'last_analysis_stats': {'malicious': 3, 'suspicious': 1, 'harmless': 2}}}}, True),
])
def test_virustotal_distingue_url_desconocida_y_analizada(monkeypatch, transporte, estado, datos, esperado):
    monkeypatch.setattr(vt.settings, 'VIRUSTOTAL_KEY', 'prueba')
    peticiones = transporte([(estado, datos)])
    r = asyncio.run(vt.consultar_virustotal('https://example.com'))
    assert r['es_conocida'] is esperado
    assert r['maliciosos'] == (3 if esperado else 0)
    assert peticiones[0].headers['x-apikey'] == 'prueba'
    assert '=' not in peticiones[0].url.path


@pytest.mark.parametrize('fallo', [httpx.ReadTimeout('sin respuesta'), (200, {'formato': 'invalido'})])
def test_virustotal_error_de_red_o_datos_no_inventa_conteo(monkeypatch, transporte, fallo):
    monkeypatch.setattr(vt.settings, 'VIRUSTOTAL_KEY', 'prueba')
    transporte([fallo])
    r = asyncio.run(vt.consultar_virustotal('https://example.com'))
    assert r.get('error')
    assert 'maliciosos' not in r


def test_phishtank_exige_confirmacion_y_reintenta_variacion(transporte):
    transporte([(200, {'results': {'in_database': True, 'valid': False}}), (200, {'results': {'in_database': True, 'valid': True, 'phish_id': 12}})])
    r = asyncio.run(pt.consultar_phishtank('https://example.com/'))
    assert r['es_phishing'] is True
    assert r['phish_id'] == 12


def test_phishtank_ausencia_de_reporte_confirmado(transporte):
    peticiones = transporte([(200, {'results': {}}), (200, {'results': {'in_database': True, 'valid': False}})])
    assert asyncio.run(pt.consultar_phishtank('https://example.com'))['es_phishing'] is False
    assert len(peticiones) == 2


def test_phishtank_una_variacion_fallida_permite_otra_valida(transporte):
    transporte([httpx.ReadTimeout('timeout'), (200, {'results': {'in_database': True, 'valid': True}})])
    assert asyncio.run(pt.consultar_phishtank('https://example.com'))['es_phishing'] is True


def test_phishtank_todos_los_intentos_fallidos_no_se_presentan_como_limpios(transporte):
    transporte([httpx.ReadTimeout('timeout'), (503, {})])
    r = asyncio.run(pt.consultar_phishtank('https://example.com'))
    assert r.get('error')


def test_phishtank_fallo_creacion_cliente_se_controla(monkeypatch):
    def fallar(*a, **kw):
        raise RuntimeError('no hay cliente')
    monkeypatch.setattr(httpx, 'AsyncClient', fallar)
    assert asyncio.run(pt.consultar_phishtank('https://example.com'))['error']


@pytest.fixture
def fecha_fija(monkeypatch):
    original = datetime.datetime
    class Fecha(original):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 26)
    monkeypatch.setattr(whois.datetime, 'datetime', Fecha)


@pytest.mark.parametrize('dominio,fecha,esperado', [
    ('https://www.example.com', '2026-10-16T00:00:00Z', 10),
    ('example.org', '2026-10-28T00:00:00Z', 0),
])
def test_rdap_calcula_antiguedad_y_no_permite_dias_negativos(transporte, fecha_fija, dominio, fecha, esperado):
    peticiones = transporte([(200, {'events': [{'eventAction': 'registration', 'eventDate': fecha}]})])
    r = asyncio.run(whois.obtener_info_whois(dominio))
    assert r['datos']['dias_antiguedad'] == esperado
    assert 'www.' not in str(peticiones[0].url)


def test_rdap_reintenta_endpoint_al_fallar_y_busca_evento_valido(transporte, fecha_fija):
    transporte([httpx.ReadTimeout('timeout'), (200, {'events': [
        {'eventAction': 'expiration'}, {'eventAction': 'created', 'eventDate': ''},
        {'eventAction': 'registration', 'eventDate': '2026-10-16'},
    ]})])
    assert asyncio.run(whois.obtener_info_whois('example.com'))['datos']['dias_antiguedad'] == 10


@pytest.mark.parametrize('respuestas', [[(404, {}), (404, {})], [(200, {'events': []}), (200, {'events': []})]])
def test_rdap_no_inventa_antiguedad_sin_eventos(transporte, respuestas):
    transporte(respuestas)
    r = asyncio.run(whois.obtener_info_whois('example.com'))
    assert r['estado'] == 'error' and r['datos'] is None


@pytest.fixture
def certificado(monkeypatch):
    contexto = MagicMock()
    canal = contexto.wrap_socket.return_value.__enter__.return_value
    monkeypatch.setattr(tls.ssl, 'create_default_context', lambda **kw: contexto)
    monkeypatch.setattr(tls.socket, 'create_connection', MagicMock())
    return canal


@pytest.mark.parametrize('issuer,esperado', [
    (((('organizationName', 'CA de prueba'),),), 'CA de prueba'),
    (((('commonName', 'CN de prueba'),),), 'CN de prueba'), ((), 'Desconocido'),
])
def test_ssl_valida_certificado_y_emisor_sin_red(certificado, issuer, esperado):
    certificado.getpeercert.return_value = {'issuer': issuer}
    r = tls.verificar_ssl('https://EXAMPLE.COM./ruta')
    assert r['datos']['valido'] is True
    assert r['datos']['emisor'] == esperado
    assert r['datos']['hostname_analizado'] == 'example.com'


def test_ssl_certificado_ausente_no_se_considera_valido(certificado, monkeypatch):
    monkeypatch.setattr(tls, 'ca_file', None)
    certificado.getpeercert.return_value = {}
    assert tls.verificar_ssl('example.com:443/ruta')['datos']['valido'] is False


@pytest.mark.parametrize('error,estado', [
    (ssl.SSLError('negociación fallida'), 'ok'),
    (ConnectionRefusedError(), 'ok'), (socket.gaierror(), 'ok'),
    (TimeoutError(), 'error'),
])
def test_ssl_errores_se_distinguen_de_certificados_validos(certificado, monkeypatch, error, estado):
    def fallar(*a, **kw):
        raise error
    monkeypatch.setattr(tls.socket, 'create_connection', fallar)
    r = tls.verificar_ssl('example.com')
    assert r['estado'] == estado
    assert r['datos'] is None if estado == 'error' else r['datos']['valido'] is False


def test_ssl_certificado_no_confiable_conserva_motivo(certificado):
    error = ssl.SSLCertVerificationError('no confiable')
    error.verify_message = 'CA no confiable'
    certificado.do_handshake.side_effect = error
    r = tls.verificar_ssl('example.com')
    assert r['datos']['valido'] is False
    assert 'CA no confiable' in r['datos']['motivo']
