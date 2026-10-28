import { afterEach, beforeEach, expect, jest, test } from '@jest/globals';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App, { EvaluadorPrincipal } from '../src/App.jsx';
import { esperarResultado, iniciarAnalisis } from '../src/servicios/analisis.js';

jest.mock('../src/servicios/analisis.js', () => ({ iniciarAnalisis: jest.fn(), esperarResultado: jest.fn() }));
const resultado = { riesgo: { puntuacion: 1, cobertura_porcentaje: 100, evaluacion_completa: true } };
const diferido = () => { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; };
const enviar = (url = 'https://example.com') => {
  fireEvent.change(screen.getByLabelText('Enlace que quieres revisar'), { target: { value: url } });
  fireEvent.click(screen.getByRole('button', { name: 'Revisar enlace' }));
};
const fetchOriginal = globalThis.fetch;
beforeEach(() => {
  iniciarAnalisis.mockReset().mockResolvedValue('id-1');
  esperarResultado.mockReset().mockResolvedValue(resultado);
});
afterEach(() => { globalThis.fetch = fetchOriginal; });

test('A01: la pantalla inicial explica cómo comenzar', () => {
  render(<EvaluadorPrincipal />);
  expect(screen.getByText('Agrega tu primer enlace para comenzar.')).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Revisar enlace' })).not.toBeInTheDocument();
});
test.each(['example.com', 'ftp://example.com'])('A02: rechaza una entrada sin HTTP/HTTPS: %s', url => {
  render(<EvaluadorPrincipal />); enviar(url);
  expect(screen.getByRole('alert')).toHaveTextContent('Copia el enlace completo');
  expect(iniciarAnalisis).not.toHaveBeenCalled();
});
test('A03: muestra envío, progreso, resultado y vuelve a habilitar el formulario', async () => {
  const inicio = diferido(), final = diferido();
  iniciarAnalisis.mockReturnValue(inicio.promise); esperarResultado.mockReturnValue(final.promise);
  render(<EvaluadorPrincipal />); enviar('  https://example.com  ');
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
test('A04: rechaza envíos duplicados mientras hay una consulta activa', async () => {
  iniciarAnalisis.mockReturnValue(diferido().promise);
  render(<EvaluadorPrincipal />); enviar();
  fireEvent.submit(screen.getByLabelText('Enlace que quieres revisar').closest('form'));
  expect(iniciarAnalisis).toHaveBeenCalledTimes(1);
});
test.each([
  [new TypeError('red'), 'No pudimos conectarnos'],
  [new SyntaxError('json'), 'No pudimos leer el resultado'],
  [new Error('Error controlado'), 'Error controlado'],
  [new Error(''), 'No pudimos revisar este enlace.'],
])('A05: presenta el error de inicio al usuario: %s', async (error, mensaje) => {
  iniciarAnalisis.mockRejectedValue(error);
  render(<EvaluadorPrincipal />); enviar();
  expect(await screen.findByRole('alert')).toHaveTextContent(mensaje);
  expect(screen.getByText('No se pudo asignar.')).toBeVisible();
  expect(screen.getByText('Sin resultado')).toBeVisible();
  expect(screen.getByLabelText('Enlace que quieres revisar')).toBeEnabled();
});
test('A06: informa un error de seguimiento conservando el ID de la tarea', async () => {
  esperarResultado.mockRejectedValue(new Error('Tarea fallida'));
  render(<EvaluadorPrincipal />); enviar();
  expect(await screen.findByRole('alert')).toHaveTextContent('Tarea fallida');
  expect(screen.getByText('id-1')).toBeVisible();
});
test('A07: conserva revisiones anteriores al completar una nueva', async () => {
  iniciarAnalisis.mockResolvedValueOnce('primera').mockResolvedValueOnce('segunda');
  render(<EvaluadorPrincipal />); enviar();
  await screen.findByText('Finalizada');
  enviar('https://example.org');
  await waitFor(() => expect(screen.getAllByText('Finalizada')).toHaveLength(2));
  expect(screen.getByText('primera')).toBeVisible(); expect(screen.getByText('segunda')).toBeVisible();
});
test.each(['inicio', 'resultado', 'error'])('A08: desmontar cancela una consulta pendiente durante %s', async fase => {
  const inicio = diferido(), final = diferido();
  iniciarAnalisis.mockReturnValue(inicio.promise); esperarResultado.mockReturnValue(final.promise);
  const vista = render(<EvaluadorPrincipal />); enviar();
  const signal = iniciarAnalisis.mock.calls[0][1];
  if (fase !== 'inicio') await act(async () => inicio.resolve('id'));
  vista.unmount(); expect(signal.aborted).toBe(true);
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
  globalThis.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ logs: ['Evento de prueba'] }) });
  render(<MemoryRouter initialEntries={['/logs']}><App /></MemoryRouter>);
  expect(await screen.findByText('Evento de prueba')).toBeVisible();
});
