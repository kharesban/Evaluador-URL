import { afterEach, beforeEach, expect, jest, test } from '@jest/globals';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import VerLogs from '../src/verLogs.jsx';

const original = globalThis.fetch;
const mostrar = () => render(<MemoryRouter><VerLogs /></MemoryRouter>);
beforeEach(() => { jest.useFakeTimers(); globalThis.fetch = jest.fn(); });
afterEach(() => { jest.clearAllTimers(); jest.useRealTimers(); globalThis.fetch = original; jest.restoreAllMocks(); });
test('L01: indica carga y después muestra los registros recibidos', async () => {
  let resolver;
  fetch.mockReturnValue(new Promise(resolve => { resolver = resolve; }));
  mostrar(); expect(screen.getByText('Cargando registros del servidor...')).toBeVisible();
  await act(async () => resolver({ ok: true, json: async () => ({ logs: ['Uno', 'Dos'] }) }));
  expect(screen.getByText(/Uno.*Dos/)).toBeVisible();
  expect(fetch).toHaveBeenCalledWith('http://localhost:8000/logs', { cache: 'no-store' });
  expect(screen.getByRole('link', { name: /Volver al Evaluador/ })).toHaveAttribute('href', '/');
});
test.each([[], undefined])('L02: muestra ausencia de registros para %p', async logs => {
  fetch.mockResolvedValue({ ok: true, json: async () => ({ logs }) });
  await act(async () => mostrar());
  expect(screen.getByText('No hay registros disponibles.')).toBeVisible();
});
test.each(['http', 'red'])('L03: termina la carga ante un error %s', async tipo => {
  jest.spyOn(console, 'error').mockImplementation(() => {});
  if (tipo === 'http') fetch.mockResolvedValue({ ok: false });
  else fetch.mockRejectedValue(new Error('sin red'));
  await act(async () => mostrar());
  expect(screen.queryByText('Cargando registros del servidor...')).not.toBeInTheDocument();
  expect(screen.getByText('No hay registros disponibles.')).toBeVisible();
  if (tipo === 'red') expect(console.error).toHaveBeenCalled();
});
test('L04: actualiza cada dos segundos, permite pausa y actualización manual', async () => {
  fetch.mockResolvedValue({ ok: true, json: async () => ({ logs: [] }) });
  await act(async () => mostrar()); expect(fetch).toHaveBeenCalledTimes(1);
  await act(async () => jest.advanceTimersByTimeAsync(2000)); expect(fetch).toHaveBeenCalledTimes(2);
  await act(async () => fireEvent.click(screen.getByRole('checkbox')));
  const pausado = fetch.mock.calls.length;
  await act(async () => jest.advanceTimersByTimeAsync(6000)); expect(fetch).toHaveBeenCalledTimes(pausado);
  await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Refrescar' })));
  expect(fetch).toHaveBeenCalledTimes(pausado + 1);
});
test('L05: desmontar elimina el intervalo de actualización', async () => {
  fetch.mockResolvedValue({ ok: true, json: async () => ({ logs: [] }) });
  let vista; await act(async () => { vista = mostrar(); });
  vista.unmount(); const llamadas = fetch.mock.calls.length;
  await act(async () => jest.advanceTimersByTimeAsync(6000));
  expect(fetch).toHaveBeenCalledTimes(llamadas); expect(jest.getTimerCount()).toBe(0);
});
