import { useCallback, useEffect, useRef, useState } from "react";
import { Routes, Route, Link } from "react-router-dom";
import {
  iniciarAnalisis,
  esperarResultado,
} from "./servicios/analisis.js";
import { listarRevisiones, TAMANO_PAGINA } from "./servicios/historial.js";
import VerLogs from "./verLogs.jsx";
import Reporte from "./Reporte.jsx";
import ResultadoRevision from "./componentes/ResultadoRevision.jsx";
import "./App.css";

function explicarError(error) {
  if (error instanceof TypeError) {
    return "No pudimos conectarnos para revisar tu enlace. Intenta nuevamente en unos momentos.";
  }
  if (error instanceof SyntaxError) {
    return "No pudimos leer el resultado. Intenta nuevamente.";
  }
  return error.message || "No pudimos revisar este enlace.";
}

export function EvaluadorPrincipal() {
  const [url, setUrl] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [revisiones, setRevisiones] = useState([]);
  const [totalRevisiones, setTotalRevisiones] = useState(0);
  const [cargandoHistorial, setCargandoHistorial] = useState(true);
  const [cargandoMas, setCargandoMas] = useState(false);
  const [analisisLocalActivo, setAnalisisLocalActivo] = useState(false);
  const [avisoHistorial, setAvisoHistorial] = useState("");
  const consultasActivas = useRef(new Map());
  const envioActivo = useRef(false);

  const actualizarRevision = useCallback((clave, cambios) => {
    setRevisiones((anteriores) => {
      const actualizadas = anteriores.map((revision) =>
        revision.clave === clave ? { ...revision, ...cambios } : revision,
      );
      // Si la consulta inicial alcanzó a traer la tarea antes de recibir su ID,
      // evita mostrar dos tarjetas para el mismo registro del servidor.
      if (!cambios.id) return actualizadas;
      return actualizadas.filter(
        (revision) => revision.clave === clave || revision.id !== cambios.id,
      );
    });
  }, []);

  const seguirRevision = useCallback(async (revision, signal) => {
    try {
      const resultado = await esperarResultado(revision.id, signal);
      if (signal.aborted) return;
      actualizarRevision(revision.clave, {
        estado: "completado",
        resultado,
        error: "",
      });
    } catch (error) {
      if (signal.aborted) return;
      // Los fallos transitorios se pueden volver a consultar al recargar el historial.
      actualizarRevision(revision.clave, {
        estado: "error",
        error: explicarError(error),
      });
    }
  }, [actualizarRevision]);

  const iniciarSeguimiento = useCallback((revision) => {
    if (!revision.id || consultasActivas.current.has(revision.clave)) return;

    const controlador = new AbortController();
    consultasActivas.current.set(revision.clave, { controlador });
    seguirRevision(revision, controlador.signal).finally(() => {
      if (consultasActivas.current.get(revision.clave)?.controlador === controlador) {
        consultasActivas.current.delete(revision.clave);
      }
    });
  }, [seguirRevision]);

  useEffect(() => {
    const controlador = new AbortController();
    const consultas = consultasActivas.current;

    async function cargarHistorialInicial() {
      try {
        const pagina = await listarRevisiones({
          limit: TAMANO_PAGINA,
          offset: 0,
          signal: controlador.signal,
        });
        if (controlador.signal.aborted) return;

        setRevisiones((anteriores) => {
          const idsExistentes = new Set(
            anteriores.map((revision) => revision.id).filter(Boolean),
          );
          const nuevas = pagina.items.filter((revision) => !idsExistentes.has(revision.id));
          return [...anteriores, ...nuevas].sort((a, b) => b.fecha - a.fecha);
        });
        setTotalRevisiones((actual) => Math.max(actual, pagina.total));
        for (const revision of pagina.items) {
          if (revision.estado === "en_proceso") iniciarSeguimiento(revision);
        }
      } catch (error) {
        if (!controlador.signal.aborted) {
          setAvisoHistorial(error.message || "No se pudo cargar el historial compartido.");
        }
      } finally {
        if (!controlador.signal.aborted) setCargandoHistorial(false);
      }
    }

    cargarHistorialInicial();

    return () => {
      controlador.abort();
      for (const { controlador: consulta } of consultas.values()) {
        consulta.abort();
      }
      consultas.clear();
    };
  }, [iniciarSeguimiento]);

  async function cargarMasRevisiones() {
    setCargandoMas(true);
    setAvisoHistorial("");
    try {
      const offset = revisiones.filter((revision) => revision.id).length;
      const pagina = await listarRevisiones({ limit: TAMANO_PAGINA, offset });
      setRevisiones((anteriores) => {
        const ids = new Set(anteriores.map((revision) => revision.id).filter(Boolean));
        const nuevas = pagina.items.filter((revision) => !ids.has(revision.id));
        return [...anteriores, ...nuevas];
      });
      setTotalRevisiones(pagina.total);
      for (const revision of pagina.items) {
        if (revision.estado === "en_proceso") iniciarSeguimiento(revision);
      }
    } catch (error) {
      setAvisoHistorial(error.message || "No se pudieron cargar más evaluaciones.");
    } finally {
      setCargandoMas(false);
    }
  }

  async function analizarURL(evento) {
    evento.preventDefault();
    if (envioActivo.current) return;

    setMensaje("");
    const urlLimpia = url.trim();

    if (!/^https?:\/\//i.test(urlLimpia)) {
      setMensaje(
        "Copia el enlace completo desde tu navegador. Por ejemplo: https://ejemplo.com",
      );
      return;
    }

    envioActivo.current = true;
    setAnalisisLocalActivo(true);
    const clave = crypto.randomUUID();
    const controlador = new AbortController();
    const { signal } = controlador;

    consultasActivas.current.set(clave, { controlador, url: urlLimpia });
    setRevisiones((anteriores) => [
      {
        clave,
        url: urlLimpia,
        id: "",
        fecha: Date.now(),
        estado: "enviando",
        resultado: null,
        error: "",
      },
      ...anteriores,
    ]);
    setUrl("");

    try {
      const tareaId = await iniciarAnalisis(urlLimpia, signal);
      if (signal.aborted) return;

      const revision = {
        clave,
        id: tareaId,
        url: urlLimpia,
        fecha: Date.now(),
        estado: "en_proceso",
        resultado: null,
        error: "",
      };
      actualizarRevision(clave, revision);
      setTotalRevisiones((total) => total + 1);
      await seguirRevision(revision, signal);
    } catch (error) {
      if (!signal.aborted) {
        actualizarRevision(clave, {
          estado: "error",
          error: explicarError(error),
        });
      }
    } finally {
      consultasActivas.current.delete(clave);
      envioActivo.current = false;
      setAnalisisLocalActivo(false);
    }
  }

  const pendientes = revisiones.filter(
    (revision) => revision.estado === "enviando" || revision.estado === "en_proceso",
  ).length;

  return (
    <main className="container">
      <header className="cabecera">
        <h1>Revisa tus enlaces</h1>
        <p>Analiza enlaces y consulta el historial compartido de evaluaciones.</p>
      </header>

      <div className="panel-revisiones">
        <section className="nuevo-analisis" aria-labelledby="titulo-nueva">
          <h2 id="titulo-nueva">Nueva revisión</h2>
          <p>Pega un enlace. Buscaremos señales que puedan indicar un riesgo.</p>

          <form className="formulario-url" onSubmit={analizarURL}>
            <label htmlFor="url-analisis">Enlace que quieres revisar</label>
            <input
              id="url-analisis"
              type="text"
              placeholder="https://ejemplo.com"
              value={url}
              onChange={(evento) => setUrl(evento.target.value)}
              disabled={analisisLocalActivo}
              aria-describedby="ayuda-enlace"
            />
            {url.trim() !== "" && (
              <button type="submit" disabled={analisisLocalActivo}>
                {analisisLocalActivo ? "Revisando..." : "Revisar enlace"}
              </button>
            )}
          </form>

          <p id="ayuda-enlace" className="ayuda">
            Cuando termine esta revisión, podrás enviar otro enlace.
          </p>
          {mensaje && <p className="error" role="alert">{mensaje}</p>}
        </section>

        <section className="lista-revisiones" aria-labelledby="titulo-revisiones">
          <h2 id="titulo-revisiones">Historial compartido</h2>
          <p className="resumen-revisiones" role="status">
            {cargandoHistorial
              ? "Cargando historial compartido..."
              : revisiones.length === 0
                ? "Todavía no hay evaluaciones guardadas en el servidor."
                : `${pendientes} en curso · ${revisiones.length - pendientes} finalizadas o sin resultado · ${totalRevisiones} en total`}
          </p>

          {avisoHistorial && <p className="error" role="alert">{avisoHistorial}</p>}

          {!cargandoHistorial && !avisoHistorial && revisiones.length === 0 && (
            <div className="tarjeta-vacia">Agrega el primer enlace para comenzar el historial compartido.</div>
          )}

          {revisiones.map((revision) => {
            const enCurso = revision.estado === "enviando" || revision.estado === "en_proceso";
            const etiqueta = revision.estado === "enviando"
              ? "Enviando"
              : revision.estado === "en_proceso"
                ? "En revisión"
                : revision.estado === "completado"
                  ? "Finalizada"
                  : "Sin resultado";

            return (
              <article className="tarjeta-revision" key={revision.clave}>
                <div className="tarjeta-cabecera">
                  <h3>{revision.url || "Enlace no disponible"}</h3>
                  <span className={`etiqueta etiqueta--${revision.estado}`}>{etiqueta}</span>
                </div>

                <div className="identificador-revision">
                  <p>Identificador de la revisión</p>
                  {revision.id ? <code>{revision.id}</code> : <p>{revision.estado === "enviando" ? "Se asignará al iniciar." : "No se pudo asignar."}</p>}
                </div>

                {enCurso && (
                  <div className="estado-analisis" role="status">
                    <p>{revision.estado === "enviando" ? "Enviando tu enlace…" : "Estamos revisando este enlace…"}</p>
                    <progress aria-label={`Revisión en curso de ${revision.url}`} />
                    <p>El resultado aparecerá aquí cuando termine.</p>
                  </div>
                )}

                {revision.error && <p className="error" role="alert">{revision.error}</p>}
                {revision.resultado && (
                  <ResultadoRevision resultado={revision.resultado} tareaId={revision.id} />
                )}
                {!revision.resultado && revision.estado === "completado" && revision.id && (
                  <p><Link to={`/reporte/${encodeURIComponent(revision.id)}`}>Abrir reporte completo</Link></p>
                )}
              </article>
            );
          })}

          {!cargandoHistorial && revisiones.length < totalRevisiones && (
            <button type="button" onClick={cargarMasRevisiones} disabled={cargandoMas}>
              {cargandoMas ? "Cargando..." : "Cargar más evaluaciones"}
            </button>
          )}

          <p className="ayuda">
            Este historial es compartido: todas las personas que accedan a la aplicación pueden consultar las evaluaciones y sus reportes.
          </p>
        </section>
      </div>
    </main>
  );
}

// ==========================================
// RUTAS PRINCIPALES DE LA APLICACIÓN
// ==========================================
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<EvaluadorPrincipal />} />
      <Route path="/logs" element={<VerLogs />} />
      <Route path="/reporte/:tareaId" element={<Reporte />} />
    </Routes>
  );
}
