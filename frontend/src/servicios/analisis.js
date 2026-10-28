import { API_URL } from "./config.js";
const INTERVALO_CONSULTA_MS = 1000;
const MAXIMO_CONSULTAS = 30;

// Paso 1: solicitar un análisis y recibir el identificador de la tarea.
export async function iniciarAnalisis(url, signal) {
  const respuesta = await fetch(`${API_URL}/analizar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
    signal,
  });

  if (!respuesta.ok) {
    throw new Error("No se pudo iniciar el análisis. Revisa la URL.");
  }

  const tarea = await respuesta.json();

  if (typeof tarea.id !== "string" || !tarea.id.trim()) {
    throw new Error("El servidor no devolvió el identificador del análisis.");
  }

  return tarea.id;
}

// Paso 2: preguntar al servidor cómo va una tarea concreta.
export async function consultarEstadoTarea(tareaId, signal) {
  const respuesta = await fetch(
    `${API_URL}/tareas/${encodeURIComponent(tareaId)}`,
    { cache: "no-store", signal },
  );

  if (!respuesta.ok) {
    throw new Error("No se pudo consultar el análisis. Intenta nuevamente.");
  }

  return respuesta.json();
}

// Pausa entre consultas. También se cancela al salir de la pantalla.
function esperar(milisegundos, signal) {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(signal.reason);
      return;
    }

    const temporizador = setTimeout(() => {
      signal.removeEventListener("abort", cancelarEspera);
      resolve();
    }, milisegundos);

    function cancelarEspera() {
      clearTimeout(temporizador);
      reject(signal.reason);
    }

    signal.addEventListener("abort", cancelarEspera, { once: true });
  });
}

// Paso 3: repetir la consulta hasta obtener un resultado o un error.
export async function esperarResultado(tareaId, signal) {
  for (let consulta = 1; consulta <= MAXIMO_CONSULTAS; consulta++) {
    await esperar(INTERVALO_CONSULTA_MS, signal);
    const tarea = await consultarEstadoTarea(tareaId, signal);

    switch (tarea.estado) {
      case "completado":
        if (!tarea.resultado) {
          throw new Error("El análisis terminó, pero no se recibió el resultado.");
        }
        return tarea.resultado;

      case "error":
        throw new Error(tarea.mensaje || "No fue posible completar el análisis.");

      case "en_proceso":
        break; // Todavía no termina: esperar y consultar de nuevo.

      default:
        throw new Error("El servidor devolvió un estado desconocido.");
    }
  }

  throw new Error(
    "Dejamos de consultar después de varios intentos. El análisis podría seguir en proceso.",
  );
}
