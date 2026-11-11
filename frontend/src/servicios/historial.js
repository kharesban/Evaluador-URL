import { API_URL } from "./config.js";

const TAMANO_PAGINA = 50;

function normalizarRevision(revision) {
  const fechaRecibida = revision.fecha == null ? Number.NaN : Number(revision.fecha);
  const fecha = Number.isFinite(fechaRecibida)
    ? fechaRecibida
    : revision.fecha_creacion
      ? new Date(revision.fecha_creacion).getTime()
      : Date.now();

  return {
    ...revision,
    clave: revision.id,
    fecha: Number.isFinite(fecha) ? fecha : Date.now(),
    error: revision.mensaje || revision.error || "",
  };
}

async function leerRespuesta(respuesta, mensajeError) {
  if (!respuesta.ok) {
    throw new Error(mensajeError);
  }
  return respuesta.json();
}

/** Recupera una página del historial compartido almacenado en el backend. */
export async function listarRevisiones({
  limit = TAMANO_PAGINA,
  offset = 0,
  signal,
} = {}) {
  const parametros = new URLSearchParams({
    limit: String(Math.min(Math.max(Number(limit) || TAMANO_PAGINA, 1), 100)),
    offset: String(Math.max(Number(offset) || 0, 0)),
  });
  const respuesta = await fetch(`${API_URL}/tareas?${parametros.toString()}`, {
    cache: "no-store",
    signal,
  });
  const datos = await leerRespuesta(
    respuesta,
    "No se pudo cargar el historial compartido. Intenta nuevamente.",
  );

  if (!Array.isArray(datos.items)) {
    throw new TypeError("El servidor devolvió un historial con formato inválido.");
  }

  return {
    items: datos.items.map(normalizarRevision),
    total: Number(datos.total) || 0,
    limit: Number(datos.limit) || parametros.get("limit"),
    offset: Number(datos.offset) || 0,
  };
}

export { TAMANO_PAGINA };
