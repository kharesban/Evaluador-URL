import { useEffect, useRef, useState } from "react";
import { Routes, Route } from "react-router-dom";
import {
  iniciarAnalisis,
  esperarResultado,
} from "./servicios/analisis.js";
import VerLogs from "./verLogs.jsx";
import Reporte from "./Reporte.jsx";
import ResultadoRevision from "./componentes/ResultadoRevision.jsx";
import "./App.css";

export function EvaluadorPrincipal() {
  const [url, setUrl] = useState("");
  const [mensaje, setMensaje] = useState("");

  const [revisiones, setRevisiones] = useState([]);
  const consultasActivas = useRef(new Map());

  useEffect(() => {
    const consultas = consultasActivas.current;
    return () => {
      for (const { controlador } of consultas.values()) {
        controlador.abort();
      }
      consultas.clear();
    };
  }, []);

  function actualizarRevision(clave, cambios) {
    setRevisiones((anteriores) =>
      anteriores.map((revision) =>
        revision.clave === clave
          ? { ...revision, ...cambios }
          : revision
      )
    );
  }

  async function analizarURL(evento) {
    evento.preventDefault();
    if (consultasActivas.current.size > 0) return;

    setMensaje("");
    const urlLimpia = url.trim();

    if (!/^https?:\/\//i.test(urlLimpia)) {
      setMensaje(
        "Copia el enlace completo desde tu navegador. Por ejemplo: https://ejemplo.com"
      );
      return;
    }

    const clave = crypto.randomUUID();
    const controlador = new AbortController();
    const { signal } = controlador;

    consultasActivas.current.set(clave, {
      controlador,
      url: urlLimpia,
    });

    setRevisiones((anteriores) => [
      {
        clave,
        url: urlLimpia,
        id: "",
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

      actualizarRevision(clave, {
        id: tareaId,
        estado: "en_proceso",
      });

      const resultado = await esperarResultado(tareaId, signal);
      if (signal.aborted) return;

      actualizarRevision(clave, {
        estado: "completado",
        resultado,
      });
    } catch (error) {
      if (signal.aborted) return;

      const explicacion =
        error instanceof TypeError
          ? "No pudimos conectarnos para revisar tu enlace. Intenta nuevamente en unos momentos."
          : error instanceof SyntaxError
            ? "No pudimos leer el resultado. Intenta nuevamente."
            : error.message || "No pudimos revisar este enlace.";

      actualizarRevision(clave, {
        estado: "error",
        error: explicacion,
      });
    } finally {
      consultasActivas.current.delete(clave);
    }
  }

  const pendientes = revisiones.filter(
    (revision) =>
      revision.estado === "enviando" ||
      revision.estado === "en_proceso"
  ).length;

  const revisando = pendientes > 0;

  return (
    <main className="container">
      <header className="cabecera">
        <h1>Revisa tus enlaces</h1>
        <p>Revisa un enlace y consulta su resultado.</p>
      </header>

      <div className="panel-revisiones">
        <section
          className="nuevo-analisis"
          aria-labelledby="titulo-nueva"
        >
          <h2 id="titulo-nueva">Nueva revisión</h2>

          <p>
            Pega un enlace. Buscaremos señales que puedan indicar un riesgo.
          </p>

          <form className="formulario-url" onSubmit={analizarURL}>
            <label htmlFor="url-analisis">
              Enlace que quieres revisar
            </label>

            <input
              id="url-analisis"
              type="text"
              placeholder="https://ejemplo.com"
              value={url}
              onChange={(evento) => setUrl(evento.target.value)}
              disabled={revisando}
              aria-describedby="ayuda-enlace"
            />

            {url.trim() !== "" && (
              <button type="submit" disabled={revisando}>
                {revisando ? "Revisando..." : "Revisar enlace"}
              </button>
            )}
          </form>

          <p id="ayuda-enlace" className="ayuda">
            Cuando termine esta revisión, podrás revisar otro enlace.
          </p>

          {mensaje && (
            <p className="error" role="alert">
              {mensaje}
            </p>
          )}
        </section>

        <section
          className="lista-revisiones"
          aria-labelledby="titulo-revisiones"
        >
          <h2 id="titulo-revisiones">Mis revisiones</h2>

          <p className="resumen-revisiones" role="status">
            {revisiones.length === 0
              ? "Aquí aparecerán tus enlaces y sus resultados."
              : `${pendientes} en curso · ${
                  revisiones.length - pendientes
                } finalizadas o sin resultado`}
          </p>

          {revisiones.length === 0 && (
            <div className="tarjeta-vacia">
              Agrega tu primer enlace para comenzar.
            </div>
          )}

          {revisiones.map((revision) => {
            const enCurso =
              revision.estado === "enviando" ||
              revision.estado === "en_proceso";

            const etiqueta =
              revision.estado === "enviando"
                ? "Enviando"
                : revision.estado === "en_proceso"
                  ? "En revisión"
                  : revision.estado === "completado"
                    ? "Finalizada"
                    : "Sin resultado";

            return (
              <article className="tarjeta-revision" key={revision.clave}>
                <div className="tarjeta-cabecera">
                  <h3>{revision.url}</h3>

                  <span
                    className={`etiqueta etiqueta--${revision.estado}`}
                  >
                    {etiqueta}
                  </span>
                </div>

                <div className="identificador-revision">
                  <p>Identificador de la revisión</p>

                  {revision.id ? (
                    <code>{revision.id}</code>
                  ) : (
                    <p>
                      {revision.estado === "enviando"
                        ? "Se asignará al iniciar."
                        : "No se pudo asignar."}
                    </p>
                  )}
                </div>

                {enCurso && (
                  <div className="estado-analisis" role="status">
                    <p>
                      {revision.estado === "enviando"
                        ? "Enviando tu enlace…"
                        : "Estamos revisando tu enlace…"}
                    </p>

                    <progress
                      aria-label={`Revisión en curso de ${revision.url}`}
                    />

                    <p>El resultado aparecerá aquí cuando termine.</p>
                  </div>
                )}

                {revision.error && (
                  <p className="error" role="alert">
                    {revision.error}
                  </p>
                )}

                {revision.resultado && (
                  <ResultadoRevision resultado={revision.resultado} tareaId={revision.id} />
                )}
              </article>
            );
          })}

          <p className="ayuda">
            Esta lista se conserva mientras mantengas abierta
            la página, sin recargarla.
          </p>
        </section>
      </div>
    </main>
  );
}

// ==========================================
// 4. RUTAS PRINCIPALES DE LA APLICACIÓN
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