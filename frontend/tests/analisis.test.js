import { afterEach, beforeEach, describe, expect, jest, test } from '@jest/globals';
import { consultarEstadoTarea, esperarResultado, iniciarAnalisis } from '../src/servicios/analisis.js';

const fetchOriginal = globalThis.fetch;
const respuesta = (datos, ok = true) => ({ ok, json: jest.fn().mockResolvedValue(datos) });

beforeEach(() => {
  jest.useFakeTimers();
  globalThis.fetch = jest.fn();
});

afterEach(() => {
  jest.clearAllTimers();
  jest.useRealTimers();
  globalThis.fetch = fetchOriginal;
});

describe('HU15: solicitar y seguir una revisión', () => {
  test('J01: envía la URL y conserva el identificador devuelto por el servidor', async () => {
    const signal = new AbortController().signal;
    fetch.mockResolvedValue(respuesta({ id: 'tarea-123' }));
    await expect(iniciarAnalisis('https://example.com', signal)).resolves.toBe('tarea-123');
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/analizar', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: 'https://example.com' }), signal,
    });
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  test.each([
    ['J02a', undefined], ['J02b', null], ['J02c', ''], ['J02d', '   '], ['J02e', 123],
  ])('%s: rechaza un identificador ausente o inválido (%p)', async (_, id) => {
    fetch.mockResolvedValue(respuesta({ id }));
    await expect(iniciarAnalisis('https://example.com', new AbortController().signal))
      .rejects.toThrow('El servidor no devolvió el identificador');
  });

  test('J03: rechaza un error HTTP al iniciar sin aceptar el resultado', async () => {
    const res = respuesta({ id: 'no-aceptar' }, false);
    fetch.mockResolvedValue(res);
    await expect(iniciarAnalisis('https://example.com', new AbortController().signal))
      .rejects.toThrow('No se pudo iniciar');
    expect(res.json).not.toHaveBeenCalled();
  });

  test('J04: propaga el error de red sin inventar un identificador', async () => {
    fetch.mockRejectedValue(new TypeError('Sin conexión'));
    await expect(iniciarAnalisis('https://example.com', new AbortController().signal))
      .rejects.toThrow(TypeError);
  });

  test('J05: propaga una respuesta JSON ilegible', async () => {
    fetch.mockResolvedValue({ ok: true, json: jest.fn().mockRejectedValue(new SyntaxError('JSON inválido')) });
    await expect(iniciarAnalisis('https://example.com', new AbortController().signal))
      .rejects.toThrow(SyntaxError);
  });

  test('J06: consulta la tarea correcta, codifica su ID y desactiva la caché', async () => {
    const signal = new AbortController().signal;
    fetch.mockResolvedValue(respuesta({ estado: 'en_proceso' }));
    await expect(consultarEstadoTarea('a/b c', signal)).resolves.toEqual({ estado: 'en_proceso' });
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/tareas/a%2Fb%20c', { cache: 'no-store', signal });
  });

  test('J07: rechaza un error HTTP durante la consulta', async () => {
    fetch.mockResolvedValue(respuesta({}, false));
    await expect(consultarEstadoTarea('id', new AbortController().signal))
      .rejects.toThrow('No se pudo consultar');
  });

  test('J08: entrega el resultado cuando la tarea termina y respeta el intervalo', async () => {
    const resultado = { riesgo: { puntuacion: 2.6 } };
    fetch.mockResolvedValue(respuesta({ estado: 'completado', resultado }));
    const comprobacion = expect(esperarResultado('id', new AbortController().signal)).resolves.toEqual(resultado);
    await jest.advanceTimersByTimeAsync(999);
    expect(fetch).not.toHaveBeenCalled();
    await jest.advanceTimersByTimeAsync(1);
    await comprobacion;
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  test('J09: sigue esperando si está en proceso y deja de consultar al completar', async () => {
    fetch.mockResolvedValueOnce(respuesta({ estado: 'en_proceso' }))
      .mockResolvedValueOnce(respuesta({ estado: 'completado', resultado: { correcto: true } }));
    const comprobacion = expect(esperarResultado('id', new AbortController().signal)).resolves.toEqual({ correcto: true });
    await jest.advanceTimersByTimeAsync(1000);
    expect(fetch).toHaveBeenCalledTimes(1);
    await jest.advanceTimersByTimeAsync(1000);
    await comprobacion;
    await jest.advanceTimersByTimeAsync(5000);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  test('J10: rechaza una tarea completada que no trae resultado', async () => {
    fetch.mockResolvedValue(respuesta({ estado: 'completado' }));
    const comprobacion = expect(esperarResultado('id', new AbortController().signal)).rejects.toThrow('no se recibió el resultado');
    await jest.advanceTimersByTimeAsync(1000);
    await comprobacion;
  });

  test.each([
    ['J11', 'Consulta rechazada', 'Consulta rechazada'],
    ['J12', undefined, 'No fue posible completar el análisis.'],
  ])('%s: comunica el error de procesamiento (%p)', async (_, mensaje, esperado) => {
    fetch.mockResolvedValue(respuesta({ estado: 'error', mensaje }));
    const comprobacion = expect(esperarResultado('id', new AbortController().signal)).rejects.toThrow(esperado);
    await jest.advanceTimersByTimeAsync(1000);
    await comprobacion;
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  test('J13: rechaza un estado desconocido', async () => {
    fetch.mockResolvedValue(respuesta({ estado: 'estado-invalido' }));
    const comprobacion = expect(esperarResultado('id', new AbortController().signal)).rejects.toThrow('estado desconocido');
    await jest.advanceTimersByTimeAsync(1000);
    await comprobacion;
  });

  test('J14: se detiene en 30 consultas sin afirmar que terminó el análisis', async () => {
    fetch.mockResolvedValue(respuesta({ estado: 'en_proceso' }));
    const comprobacion = expect(esperarResultado('id', new AbortController().signal)).rejects.toThrow('podría seguir en proceso');
    await jest.advanceTimersByTimeAsync(30000);
    await comprobacion;
    expect(fetch).toHaveBeenCalledTimes(30);
    await jest.advanceTimersByTimeAsync(5000);
    expect(fetch).toHaveBeenCalledTimes(30);
  });

  test('J15: una consulta cancelada antes de empezar no llama al servidor', async () => {
    const c = new AbortController();
    const razon = new DOMException('Cancelado', 'AbortError');
    c.abort(razon);
    await expect(esperarResultado('id', c.signal)).rejects.toBe(razon);
    expect(fetch).not.toHaveBeenCalled();
  });

  test('J16: cancelar durante la espera elimina el temporizador y evita la consulta', async () => {
    const c = new AbortController();
    const razon = new DOMException('Cancelado', 'AbortError');
    const comprobacion = expect(esperarResultado('id', c.signal)).rejects.toBe(razon);
    await jest.advanceTimersByTimeAsync(500);
    c.abort(razon);
    await comprobacion;
    await jest.advanceTimersByTimeAsync(30000);
    expect(fetch).not.toHaveBeenCalled();
    expect(jest.getTimerCount()).toBe(0);
  });

  test('J17: un error HTTP durante polling termina la espera con error', async () => {
    fetch.mockResolvedValue(respuesta({}, false));
    const comprobacion = expect(esperarResultado('id', new AbortController().signal)).rejects.toThrow('No se pudo consultar');
    await jest.advanceTimersByTimeAsync(1000);
    await comprobacion;
  });
});
