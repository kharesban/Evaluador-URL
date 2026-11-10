// Una clave por revisión evita que dos pestañas sobrescriban sus historiales.
const PREFIJO = "evaluador-url:revision:v1:";

export function guardarRevision(revision) {
  try {
    // Otra pestaña puede haber terminado la misma tarea durante el seguimiento.
    if (revision.estado !== "completado" && leerRevision(revision.id)?.estado === "completado") {
      return true;
    }
    localStorage.setItem(PREFIJO + revision.id, JSON.stringify(revision));
    return true;
  } catch {
    return false;
  }
}

export function leerRevision(id) {
  try {
    const revision = JSON.parse(localStorage.getItem(PREFIJO + id));
    if (revision?.id === id && typeof revision.url === "string" &&
        ["en_proceso", "error", "completado"].includes(revision.estado)) {
      return revision;
    }
  } catch {
    // El navegador puede restringir el almacenamiento o contener una entrada dañada.
  }
  return null;
}

export function listarRevisiones() {
  try {
    return Object.keys(localStorage)
      .filter((clave) => clave.startsWith(PREFIJO))
      .map((clave) => leerRevision(clave.slice(PREFIJO.length)))
      .filter(Boolean)
      .sort((a, b) => b.fecha - a.fecha);
  } catch {
    return [];
  }
}
