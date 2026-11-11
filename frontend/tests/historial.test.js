import { afterEach, beforeEach, expect, jest, test } from '@jest/globals';
import { listarRevisiones } from '../src/servicios/historial.js';

const fetchOriginal = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = jest.fn();
});

afterEach(() => {
  globalThis.fetch = fetchOriginal;
});

test('H01: consulta una página del historial compartido en el backend', async () => {
  const signal = new AbortController().signal;
  globalThis.fetch.mockResolvedValue({
    ok: true,
    json: async () => ({
      items: [{
        id: 'revision-1',
        estado: 'completado',
        url: 'https://example.org',
        fecha: 1760000000000,
        resultado: { riesgo: { puntuacion: 1 } },
      }],
      total: 1,
      limit: 50,
      offset: 0,
    }),
  });

  const pagina = await listarRevisiones({ limit: 50, offset: 0, signal });

  expect(globalThis.fetch).toHaveBeenCalledWith(
    'http://localhost:8000/tareas?limit=50&offset=0',
    { cache: 'no-store', signal },
  );
  expect(pagina.total).toBe(1);
  expect(pagina.items[0]).toMatchObject({
    id: 'revision-1',
    clave: 'revision-1',
    estado: 'completado',
    url: 'https://example.org',
    resultado: { riesgo: { puntuacion: 1 } },
  });
});

test('H02: transforma la fecha de creación si el servidor no envía epoch', async () => {
  globalThis.fetch.mockResolvedValue({
    ok: true,
    json: async () => ({
      items: [{ id: 'revision-2', estado: 'en_proceso', fecha_creacion: '2026-11-10T12:00:00Z' }],
      total: 1,
    }),
  });
  const pagina = await listarRevisiones();
  expect(pagina.items[0].fecha).toBe(Date.parse('2026-11-10T12:00:00Z'));
});

test('H03: informa cuando el backend no puede devolver el historial', async () => {
  globalThis.fetch.mockResolvedValue({ ok: false, status: 503 });
  await expect(listarRevisiones()).rejects.toThrow('No se pudo cargar el historial compartido');
});

test('H04: rechaza una respuesta que no contiene una lista de evaluaciones', async () => {
  globalThis.fetch.mockResolvedValue({ ok: true, json: async () => ({ items: null }) });
  await expect(listarRevisiones()).rejects.toThrow('formato inválido');
});
