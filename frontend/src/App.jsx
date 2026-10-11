import { useEffect, useRef, useState } from "react";
import {
  iniciarAnalisis,
  esperarResultado,
} from "./servicios/analisis.js";
import "./App.css";

function ResultadoRevision({ resultado }) {
  return (
    <div className="resultado">
      <h3>Resultado de la revisión</h3>

      <p>
        Nivel de riesgo:{" "}
        <strong>
          {resultado.riesgo.puntuacion == null
            ? "No tenemos información suficiente para calcularlo"
            : `${resultado.riesgo.puntuacion} de 5`}
        </strong>
      </p>

      {!resultado.riesgo.evaluacion_completa && (
        <p className="aviso">
          No pudimos completar todas las comprobaciones.
          Este resultado se basa en información limitada.
        </p>
      )}

      <p>
        1 significa menor riesgo y 5, mayor riesgo. Incluso un
        resultado de riesgo bajo no garantiza que el enlace sea seguro.
      </p>

      {resultado.hallazgos_similitud?.length > 0 && (
        <div>
          <h3>Presta atención al nombre del sitio</h3>

          {resultado.hallazgos_similitud.map((hallazgo, indice) => (
            <p key={indice}>
              {hallazgo.dominio} se parece a {hallazgo.referencia}.
              Son direcciones diferentes. Comprueba que sea el sitio
              que querías visitar; el parecido por sí solo no confirma
              un engaño.
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

function App() {
  const [url, setUrl] = useState("");
  const [mensaje, setMensaje] = useState("");

  // Conserva las revisiones realizadas durante esta sesión.
  const [revisiones, setRevisiones] = useState([]);

  // Permite detener las consultas cuando se cierra la pantalla.
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

    // No permitir otro envío mientras hay una consulta activa.
    if (consultasActivas.current.size > 0) return;

    setMensaje("");
    const urlLimpia = url.trim();

    if (!/^https?:\/\//i.test(urlLimpia)) {
      setMensaje(
        "Copia el enlace completo desde tu navegador. Por ejemplo: https://ejemplo.com"
      );
      return;
    }

    // Clave de la tarjeta antes de recibir el ID real del servidor.
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
      // Primero se inicia la revisión y se recibe su identificador.
      const tareaId = await iniciarAnalisis(urlLimpia, signal);

      if (signal.aborted) return;

      actualizarRevision(clave, {
        id: tareaId,
        estado: "en_proceso",
      });

      // Después se consulta periódicamente hasta obtener el resultado.
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

            <button type="submit" disabled={revisando}>
              {revisando ? "Revisando..." : "Revisar enlace"}
            </button>
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
                  <p>Número de revisión</p>

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
                  <ResultadoRevision resultado={revision.resultado} />
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

export default App;