import { afterEach, beforeEach, expect, jest, test } from '@jest/globals';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../src/App.jsx';
import ResultadoRevision from '../src/componentes/ResultadoRevision.jsx';

const fetchOriginal = globalThis.fetch;
const mostrar = () => render(<MemoryRouter initialEntries={['/reporte/id-prueba']}><App /></MemoryRouter>);
const responder = datos => globalThis.fetch.mockResolvedValue({ ok: true, json: async () => datos });
beforeEach(() => { globalThis.fetch = jest.fn(); });
afterEach(() => { globalThis.fetch = fetchOriginal; });

test('R01: abre el reporte real y presenta puntuación y explicación recibidas', async () => {
  responder({ id: 'id-prueba', resultado: { riesgo: { puntuacion: 4.2, explicacion_causa_efecto: ['El dominio reciente añade riesgo.'] } } });
  mostrar();
  expect(screen.getByText(/Cargando diagnóstico/)).toBeVisible();
  expect(await screen.findByText('El dominio reciente añade riesgo.')).toBeVisible();
  expect(screen.getByText('ALERTAS DETECTADAS')).toBeVisible();
  expect(screen.getByText(/4.200/)).toBeVisible();
  expect(screen.getByRole('link', { name: /Volver al Evaluador/ })).toHaveAttribute('href', '/');
  expect(globalThis.fetch).toHaveBeenCalledWith('http://localhost:8000/tareas/id-prueba', { cache: 'no-store', signal: undefined });
});

test('R02: presenta puntuación baja y ausencia de observaciones adicionales', async () => {
  responder({ id: 'id-prueba', resultado: { riesgo: { puntuacion: 1 } } });
  mostrar();
  expect(await screen.findByText('DETERMINACIÓN NORMAL')).toBeVisible();
  expect(screen.getByText(/No hay observaciones/)).toBeVisible();
});

test('R03: permite explicaciones de la respuesta anterior sin inventar una puntuación', async () => {
  responder({ id: 'id-prueba', resultado: { explicacion_causa_efecto: ['Explicación disponible.'] } });
  mostrar();
  expect(await screen.findByText('Explicación disponible.')).toBeVisible();
  expect(screen.getByText('SIN INFORMACIÓN SUFICIENTE')).toBeVisible();
  expect(screen.queryByText('DETERMINACIÓN NORMAL')).not.toBeInTheDocument();
});

test('R04: una tarea sin resultado no se presenta como un sitio normal', async () => {
  responder({ id: 'id-prueba', estado: 'en_proceso' });
  mostrar();
  expect(await screen.findByText('SIN INFORMACIÓN SUFICIENTE')).toBeVisible();
});

test('R05: una respuesta nula presenta reporte no disponible', async () => {
  responder(null); mostrar();
  expect(await screen.findByText(/No se halló la tarea/)).toBeVisible();
});

test('R06: el rechazo HTTP conserva la explicación de error del servicio', async () => {
  globalThis.fetch.mockResolvedValue({ ok: false, status: 404 }); mostrar();
  expect(await screen.findByText(/No se pudo consultar el análisis/)).toBeVisible();
  expect(screen.getByRole('link', { name: /Volver al inicio/ })).toHaveAttribute('href', '/');
});

test('R07: un error de conexión no se muestra como una evaluación correcta', async () => {
  globalThis.fetch.mockRejectedValue(new TypeError('Sin conexión')); mostrar();
  expect(await screen.findByText('Sin conexión')).toBeVisible();
});

test('R08: un JSON inválido presenta el error y termina la carga', async () => {
  globalThis.fetch.mockResolvedValue({ ok: true, json: async () => { throw new SyntaxError('JSON inválido'); } });
  mostrar();
  expect(await screen.findByText('JSON inválido')).toBeVisible();
  await waitFor(() => expect(screen.queryByText(/Cargando diagnóstico/)).not.toBeInTheDocument());
});

test('R09: la tarjeta comparte el componente probado y enlaza el reporte de la tarea', () => {
  const resultado = { riesgo: { puntuacion: 1, evaluacion_completa: true, explicacion_causa_efecto: ['Explicación accesible.'] } };
  render(<MemoryRouter><ResultadoRevision resultado={resultado} tareaId="id/con espacio" /></MemoryRouter>);
  expect(screen.getByText('Explicación accesible.')).toBeVisible();
  expect(screen.getByRole('link', { name: 'Abrir reporte completo' })).toHaveAttribute('href', '/reporte/id%2Fcon%20espacio');
});
