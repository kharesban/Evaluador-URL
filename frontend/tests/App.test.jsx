import { afterEach, beforeEach, expect, jest, test } from '@jest/globals';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App, { EvaluadorPrincipal } from '../src/App.jsx';
import {
  consultarEstadoTarea,
  esperarResultado,
  iniciarAnalisis,
} from '../src/servicios/analisis.js';

jest.mock('../src/servicios/analisis.js', () => ({
  iniciarAnalisis: jest.fn(),
  esperarResultado: jest.fn(),
  consultarEstadoTarea: jest.fn(),
}));

const resultado = {
  riesgo: { puntuacion: 1, cobertura_porcentaje: 100, evaluacion_completa: true },
};
const respuestaJson = (datos, ok = true, status = 200) => ({
  ok,
  status,
  json: async () => datos,
});
const historialVacio = () => respuestaJson({ items: [], total: 0, limit: 50, offset: 0 });
const diferido = () => {
  let resolve, reject;
  const promise = new Promise((a, b) => { resolve = a; reject = b; });
  return { promise, resolve, reject };
};
const enviar = (url = 'https://example.com') => {
  fireEvent.change(screen.getByLabelText('Enlace que quieres revisar'), { target: { value: url } });
  fireEvent.click(screen.getByRole('button', { name: 'Revisar enlace' }));
};
const fetchOriginal = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = jest.fn().mockResolvedValue(historialVacio());
  iniciarAnalisis.mockReset().mockResolvedValue('id-1');
  esperarResultado.mockReset().mockResolvedValue(resultado);
  consultarEstadoTarea.mockReset().mockResolvedValue({
    id: 'id-1', estado: 'completado', resultado,
  });
});

afterEach(() => {
  globalThis.fetch = fetchOriginal;
});

test('A01: la pantalla inicial carga el historial compartido', async () => {
  render(<MemoryRouter><EvaluadorPrincipal /></MemoryRouter>);
  expect(await screen.findByText('Agrega el primer enlace para comenzar el historial compartido.')).toBeVisible();
  expect(screen.getByRole('heading', { name: 'Historial compartido' })).toBeVisible();
  expect(globalThis.fetch).toHaveBeenCalledWith(
    'http://localhost:8000/tareas?limit=50&offset=0',
    { cache: 'no-store', signal: expect.any(AbortSignal) },
  );
  expect(screen.queryByRole('button', { name: 'Revisar enlace' })).not.toBeInTheDocument();
});

test.each(['example.com', 'ftp://example.com'])('A02: rechaza una entrada sin HTTP/HTTPS: %s', async url => {
  render(<MemoryRouter><EvaluadorPrincipal /></MemoryRouter>);
  await screen.findByText('Agrega el primer enlace para comenzar el historial compartido.');
  enviar(url);
  expect(screen.getByRole('alert')).toHaveTextContent('Copia el enlace completo');
  expect(iniciarAnalisis).not.toHaveBeenCalled();
});

test('A03: muestra envío, progreso, resultado y vuelve a habilitar el formulario', async () => {
  const inicio = diferido(), final = diferido();
  iniciarAnalisis.mockReturnValue(inicio.promise);
  esperarResultado.mockReturnValue(final.promise);
  render(<MemoryRouter><EvaluadorPrincipal /></MemoryRouter>);
  enviar('  https://example.com  ');
  expect(screen.getByText('Enviando')).toBeVisible();
  expect(screen.getByText('Se asignará al iniciar.')).toBeVisible();
  expect(screen.getByLabelText('Enlace que quieres revisar')).toBeDisabled();
  expect(screen.getByRole('progressbar')).toBeVisible();
  expect(iniciarAnalisis).toHaveBeenCalledWith('https://example.com', expect.any(AbortSignal));
  await act(async () => inicio.resolve('id-123'));
  expect(screen.getByText('En revisión')).toBeVisible();
  expect(screen.getByText('id-123')).toBeVisible();
  await act(async () => final.resolve(resultado));
  expect(screen.getByText('Finalizada')).toBeVisible();
  expect(screen.getByText(/1\.000 \/ 5/)).toBeVisible();
  expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Enlace que quieres revisar')).toBeEnabled();
});

test('A04: rechaza envíos duplicados mientras hay una consulta local activa', async () => {
  iniciarAnalisis.mockReturnValue(diferido().promise);
  render(<MemoryRouter><EvaluadorPrincipal /></MemoryRouter>);
  enviar();
  fireEvent.submit(screen.getByLabelText('Enlace que quieres revisar').closest('form'));
  expect(iniciarAnalisis).toHaveBeenCalledTimes(1);
});

test.each([
  [new TypeError('red'), 'No pudimos conectarnos'],
  [new SyntaxError('json'), 'No pudimos leer el resultado'],
  [new Error('Error controlado'), 'Error controlado'],
  [new Error(''), 'No pudimos revisar este enlace.'],
])('A05: presenta un error de inicio al usuario: %s', async (error, mensaje) => {
  iniciarAnalisis.mockRejectedValue(error);
  render(<MemoryRouter><EvaluadorPrincipal /></MemoryRouter>);
  enviar();
  expect(await screen.findByRole('alert')).toHaveTextContent(mensaje);
  expect(screen.getByText('No se pudo asignar.')).toBeVisible();
  expect(screen.getByText('Sin resultado')).toBeVisible();
  expect(screen.getByLabelText('Enlace que quieres revisar')).toBeEnabled();
});

test('A06: informa un error de seguimiento conservando el ID de la tarea', async () => {
  esperarResultado.mockRejectedValue(new Error('Tarea fallida'));
  render(<MemoryRouter><EvaluadorPrincipal /></MemoryRouter>);
  enviar();
  expect(await screen.findByRole('alert')).toHaveTextContent('Tarea fallida');
  expect(screen.getByText('id-1')).toBeVisible();
});

test('A07: conserva revisiones anteriores al completar una nueva', async () => {
  iniciarAnalisis.mockResolvedValueOnce('primera').mockResolvedValueOnce('segunda');
  render(<MemoryRouter><EvaluadorPrincipal /></MemoryRouter>);
  enviar();
  await screen.findByText('Finalizada');
  await waitFor(() => expect(screen.getByLabelText('Enlace que quieres revisar')).toBeEnabled());
  enviar('https://example.org');
  await waitFor(() => expect(screen.getAllByText('Finalizada')).toHaveLength(2));
  expect(screen.getByText('primera')).toBeVisible();
  expect(screen.getByText('segunda')).toBeVisible();
});

test.each(['inicio', 'resultado', 'error'])('A08: desmontar cancela una consulta pendiente durante %s', async fase => {
  const inicio = diferido(), final = diferido();
  iniciarAnalisis.mockReturnValue(inicio.promise);
  esperarResultado.mockReturnValue(final.promise);
  const vista = render(<MemoryRouter><EvaluadorPrincipal /></MemoryRouter>);
  enviar();
  const signal = iniciarAnalisis.mock.calls[0][1];
  if (fase !== 'inicio') await act(async () => inicio.resolve('id'));
  vista.unmount();
  expect(signal.aborted).toBe(true);
  await act(async () => {
    if (fase === 'inicio') inicio.resolve('id');
    else if (fase === 'resultado') final.resolve(resultado);
    else final.reject(new DOMException('Cancelado', 'AbortError'));
  });
  if (fase === 'inicio') expect(esperarResultado).not.toHaveBeenCalled();
});

test('A09: la ruta raíz presenta el evaluador real', () => {
  render(<MemoryRouter><App /></MemoryRouter>);
  expect(screen.getByRole('heading', { name: 'Revisa tus enlaces' })).toBeVisible();
});

test('A10: la ruta de registros presenta la vista de logs real', async () => {
  globalThis.fetch = jest.fn().mockResolvedValue(respuestaJson({ logs: ['Evento de prueba'] }));
  render(<MemoryRouter initialEntries={['/logs']}><App /></MemoryRouter>);
  expect(await screen.findByText('Evento de prueba')).toBeVisible();
});

test('recupera el reporte compartido al volver sin solicitar otro análisis', async () => {
  const vista = render(<MemoryRouter><App /></MemoryRouter>);
  enviar();
  await screen.findByText('Finalizada');
  vista.unmount();

  globalThis.fetch = jest.fn().mockResolvedValue(respuestaJson({
    items: [{
      id: 'id-1', clave: 'id-1', url: 'https://example.com', fecha: Date.now(),
      estado: 'completado', resultado,
    }],
    total: 1,
    limit: 50,
    offset: 0,
  }));
  render(<MemoryRouter><App /></MemoryRouter>);
  fireEvent.click(await screen.findByRole('link', { name: 'Abrir reporte completo' }));
  expect(await screen.findByRole('heading', { name: /Reporte de Diagnóstico/ })).toBeVisible();
  expect(screen.getByText(/1\.000/)).toBeVisible();
  expect(iniciarAnalisis).toHaveBeenCalledTimes(1);
  expect(esperarResultado).toHaveBeenCalledTimes(1);
  expect(consultarEstadoTarea).toHaveBeenCalledWith('id-1', expect.any(AbortSignal));
});

test('reanuda una consulta pendiente mediante el mismo identificador del servidor', async () => {
  globalThis.fetch = jest.fn().mockResolvedValue(respuestaJson({
    items: [{
      id: 'pendiente', clave: 'pendiente', url: 'https://example.org',
      fecha: 1, estado: 'en_proceso',
    }],
    total: 1,
    limit: 50,
    offset: 0,
  }));
  render(<MemoryRouter><App /></MemoryRouter>);
  expect(await screen.findByText('Finalizada')).toBeVisible();
  expect(esperarResultado).toHaveBeenCalledWith('pendiente', expect.any(AbortSignal));
  expect(iniciarAnalisis).not.toHaveBeenCalled();
});

test('informa cuando no puede recuperar el historial compartido', async () => {
  globalThis.fetch = jest.fn().mockResolvedValue(respuestaJson({}, false, 503));
  render(<MemoryRouter><EvaluadorPrincipal /></MemoryRouter>);
  expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo cargar el historial compartido');
});

test('muestra las evaluaciones compartidas que devuelve el servidor', async () => {
  globalThis.fetch = jest.fn().mockResolvedValue(respuestaJson({
    items: [{
      id: 'compartida-1',
      url: 'https://sitio-compartido.example',
      fecha: Date.now(),
      estado: 'completado',
      resultado,
    }],
    total: 1,
    limit: 50,
    offset: 0,
  }));
  render(<MemoryRouter><EvaluadorPrincipal /></MemoryRouter>);
  expect(await screen.findByText('https://sitio-compartido.example')).toBeVisible();
  expect(screen.getByText('Finalizada')).toBeVisible();
  expect(screen.getByText('compartida-1')).toBeVisible();
  expect(screen.getByRole('link', { name: 'Abrir reporte completo' })).toHaveAttribute(
    'href',
    '/reporte/compartida-1',
  );
});

test('permite cargar la siguiente página del historial compartido', async () => {
  const primeras = Array.from({ length: 50 }, (_, indice) => ({
    id: `pagina-1-${indice}`,
    url: `https://sitio-${indice}.example`,
    fecha: Date.now() - indice,
    estado: 'error',
    mensaje: 'No fue posible completar el análisis.',
  }));
  globalThis.fetch = jest.fn()
    .mockResolvedValueOnce(respuestaJson({ items: primeras, total: 51, limit: 50, offset: 0 }))
    .mockResolvedValueOnce(respuestaJson({
      items: [{
        id: 'pagina-2-1', url: 'https://ultimo.example', fecha: 1,
        estado: 'error', mensaje: 'No fue posible completar el análisis.',
      }],
      total: 51,
      limit: 50,
      offset: 50,
    }));

  render(<MemoryRouter><EvaluadorPrincipal /></MemoryRouter>);
  expect(await screen.findByText('https://sitio-0.example')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Cargar más evaluaciones' }));
  expect(await screen.findByText('https://ultimo.example')).toBeVisible();
  expect(globalThis.fetch).toHaveBeenLastCalledWith(
    'http://localhost:8000/tareas?limit=50&offset=50',
    { cache: 'no-store', signal: undefined },
  );
});
