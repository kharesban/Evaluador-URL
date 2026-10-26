import { useEffect, useRef, useState } from "react";
import { Link, Routes, Route, useParams } from "react-router-dom";
import {
  iniciarAnalisis,
  esperarResultado,
} from "./servicios/analisis.js";
import VerLogs from "./verLogs.jsx";
import "./App.css";

// ==========================================
// 1. COMPONENTE DE VISTA DE REPORTE INDIVIDUAL (/reporte/:tareaId)
// ==========================================
export function Reporte() {
  const { tareaId } = useParams();
  const [tarea, setTarea] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const obtenerReporte = async () => {
      try {
        const res = await fetch(`http://localhost:8000/tareas/${tareaId}`);
        if (!res.ok) {
          throw new Error("No se encontró la evaluación o el registro expiró (24h).");
        }
        const data = await res.json();
        setTarea(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setCargando(false);
      }
    };

    if (tareaId) obtenerReporte();
  }, [tareaId]);

  if (cargando) {
    return (
      <div style={{ padding: "40px", textAlign: "center" }}>
        <h2>🔍 Cargando diagnóstico explicativo...</h2>
      </div>
    );
  }

  if (error || !tarea) {
    return (
      <div style={{ padding: "40px", textAlign: "center", color: "#ff4d4d" }}>
        <h2>⚠️ Reporte no disponible</h2>
        <p>{error || "No se halló la tarea."}</p>
        <Link to="/" style={{ color: "#646cff", textDecoration: "underline" }}>
          ← Volver al inicio
        </Link>
      </div>
    );
  }

  const resultado = tarea.resultado || {};
  const explicaciones = resultado.riesgo?.explicacion_causa_efecto || resultado.explicacion_causa_efecto || [];
  const puntuacion = resultado.riesgo?.puntuacion ?? "N/A";

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", padding: "20px", textAlign: "left" }}>
      <div style={{ marginBottom: "20px" }}>
        <Link to="/" style={{ color: "#646cff", textDecoration: "none", fontWeight: "bold" }}>
          ← Volver al Evaluador
        </Link>
      </div>

      <header style={{ borderBottom: "1px solid #333", paddingBottom: "15px", marginBottom: "25px" }}>
        <h1 style={{ fontSize: "24px", marginBottom: "8px" }}>
          📋 Reporte de Diagnóstico y Causa-Efecto
        </h1>
        <p style={{ color: "#aaa", fontSize: "14px", margin: 0 }}>
          Identificador de Análisis: <code>{tarea.id}</code>
        </p>
      </header>

      {/* Tarjeta de Resumen General */}
      <div
        style={{
          backgroundColor: "#1a1a1a",
          border: "1px solid #333",
          borderRadius: "8px",
          padding: "20px",
          marginBottom: "30px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center"
        }}
      >
        <div>
          <h3 style={{ margin: "0 0 5px 0", color: "#888", fontSize: "14px" }}>ESCALA DE RIESGO OBJETIVA</h3>
          <p style={{ margin: 0, fontSize: "28px", fontWeight: "bold" }}>
            {puntuacion !== "N/A" ? Number(puntuacion).toFixed(3) : "N/A"} <span style={{ fontSize: "16px", color: "#666" }}>/ 5</span>
          </p>
        </div>
        <div style={{ textAlign: "right" }}>
          <span
            style={{
              padding: "6px 12px",
              borderRadius: "20px",
              fontSize: "12px",
              fontWeight: "bold",
              backgroundColor: puntuacion > 3 ? "#4a1212" : "#123e1b",
              color: puntuacion > 3 ? "#ff8888" : "#88ff99"
            }}
          >
            {puntuacion > 3 ? "ALERTAS DETECTADAS" : "DETERMINACIÓN NORMAL"}
          </span>
        </div>
      </div>

      {/* Sección Explicativa Causa-Efecto */}
      <section>
        <h2 style={{ fontSize: "18px", color: "#ddd", marginBottom: "15px" }}>
          💡 Hallazgos Explicados en Lenguaje Cotidiano
        </h2>

        {explicaciones.length === 0 ? (
          <p style={{ color: "#888", fontStyle: "italic" }}>
            No hay observaciones explicativas adicionales para esta evaluación.
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
            {explicaciones.map((parrafo, idx) => (
              <div
                key={idx}
                style={{
                  backgroundColor: "#242424",
                  borderLeft: "4px solid #646cff",
                  padding: "15px 20px",
                  borderRadius: "0 8px 8px 0",
                  lineHeight: "1.6",
                  color: "#e0e0e0"
                }}
              >
                {parrafo}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

// ==========================================
// 2. COMPONENTE DE RESULTADO EN LA TARJETA PRINCIPAL
// ==========================================
function ResultadoRevision({ resultado, tareaId }) {
  const tiempoEjecucion =
    resultado.tiempo_ejecucion_total_seg ?? resultado.duracion_segundos ?? null;

  const explicaciones = resultado.riesgo?.explicacion_causa_efecto || [];

  return (
    <div className="resultado">
      <h3>Resultado de la revisión</h3>
      {tiempoEjecucion != null && (
        <p><strong>Tiempo de ejecución:</strong> {tiempoEjecucion} segundos</p>
      )}

      {resultado.riesgo?.es_dominio_invalido ? (
        <div className="aviso" role="status">
          <h3>No pudimos comprobar este sitio</h3>
          <p>
            {resultado.riesgo.mensaje ||
              "La página no está registrada como un dominio válido o activo."}
          </p>
          <p>
            No se asignó una puntuación porque no pudimos confirmar que esta dirección esté activa.
          </p>
        </div>
      ) : (
        <>
          <p>
            <strong>Puntuación de riesgo:</strong>{" "}
            {resultado.riesgo?.puntuacion == null
              ? "Sin información suficiente"
              : Number(resultado.riesgo.puntuacion).toFixed(3)} / 5
          </p>

          <p>
            <strong>Cobertura del análisis:</strong> {resultado.riesgo?.cobertura_porcentaje}%
          </p>

          {/* NUEVA SECCIÓN: Explicación en lenguaje accesible en la tarjeta */}
          {explicaciones.length > 0 && (
            <div
              style={{
                backgroundColor: "#1e1e1e",
                borderLeft: "4px solid #00d26a",
                padding: "12px 15px",
                borderRadius: "4px",
                margin: "15px 0",
                textAlign: "left"
              }}
            >
              <h4 style={{ margin: "0 0 8px 0", color: "#00d26a", fontSize: "14px" }}>
                💡 Explicación del Nivel de Riesgo (Sin jerga técnica):
              </h4>
              <ul style={{ margin: 0, paddingLeft: "18px", color: "#ddd", fontSize: "13px", lineHeight: "1.5" }}>
                {explicaciones.map((item, index) => (
                  <li key={index} style={{ marginBottom: "6px" }}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {resultado.riesgo?.detalle_indicadores?.length > 0 && (
            <section className="detalle-riesgo" aria-labelledby="titulo-detalle-riesgo">
              <h3 id="titulo-detalle-riesgo">¿Por qué obtuvimos esta calificación?</h3>
              <p className="detalle-riesgo-intro">
                La puntuación se calcula con los indicadores disponibles y sus pesos. Un impacto alto representa una señal de riesgo, no una certeza de ataque.
              </p>
              <ul className="lista-detalle-riesgo">
                {resultado.riesgo.detalle_indicadores.map((detalle) => (
                  <li key={detalle.clave}>
                    <div className="detalle-riesgo-cabecera">
                      <strong>{detalle.indicador}</strong>
                      <span className={`impacto ${detalle.estado === "sin_datos" ? "impacto--sin-datos" : `impacto--${(detalle.impacto || "bajo").toLowerCase()}`}`}>
                        {detalle.estado === "sin_datos" ? "Sin datos" : `Impacto ${detalle.impacto}`}
                      </span>
                    </div>
                    <p>{detalle.explicacion}</p>
                    <small>Peso: {detalle.peso}%{detalle.estado === "evaluado" ? ` · Contribución ponderada: ${detalle.contribucion_ponderada}` : ""}</small>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {!resultado.riesgo?.evaluacion_completa && (
            <p className="error">
              Evaluación incompleta. Indicadores sin datos:{" "}
              {resultado.riesgo?.indicadores_faltantes?.join(", ")}.
            </p>
          )}

          {/* Botón para navegar al Reporte Didáctico completo */}
          {tareaId && (
            <div style={{ marginTop: "15px", marginBottom: "15px", textAlign: "center" }}>
              <Link
                to={`/reporte/${tareaId}`}
                style={{
                  display: "inline-block",
                  backgroundColor: "#646cff",
                  color: "#ffffff",
                  padding: "8px 16px",
                  borderRadius: "6px",
                  textDecoration: "none",
                  fontWeight: "bold",
                  fontSize: "13px"
                }}
              >
                📄 Abrir Reporte Completo en Pantalla Completa
              </Link>
            </div>
          )}

          <p style={{ fontSize: "12px", color: "#666" }}>
            La puntuación va de 1 a 5: 1 representa el menor riesgo y 5 el mayor. 
            Una puntuación de 1 no garantiza seguridad absoluta.
          </p>

          {resultado.fuentes && (
            <div style={{ marginTop: "15px", textAlign: "left" }}>
              <h3>Fuentes analizadas:</h3>
              <ul>
                {/* PhishTank */}
                <li>
                  <strong>PhishTank:</strong>{" "}
                  {resultado.fuentes.phishtank?.estado === "ok" ? (
                    resultado.fuentes.phishtank.datos?.es_phishing ? (
                      <span style={{ color: "red", fontWeight: "bold" }}>🚨 DETECTADO COMO PHISHING</span>
                    ) : (
                      <span style={{ color: "green" }}>Limpio / No reportado</span>
                    )
                  ) : (
                    <span style={{ color: "orange" }}>⚠️ Servicio no disponible o sin respuesta</span>
                  )}
                </li>

                {/* VirusTotal */}
                <li>
                  <strong>VirusTotal:</strong>{" "}
                  {resultado.fuentes.virustotal?.estado === "ok" ? (
                    resultado.fuentes.virustotal.datos?.maliciosos > 0 ? (
                      <span style={{ color: "red", fontWeight: "bold" }}>
                        {resultado.fuentes.virustotal.datos.maliciosos} detecciones maliciosas
                      </span>
                    ) : (
                      <span style={{ color: "green" }}>0 detecciones maliciosas</span>
                    )
                  ) : (
                    <span style={{ color: "orange" }}>⚠️ Sin respuesta</span>
                  )}
                </li>

                {/* Google Safe Browsing */}
                <li>
                  <strong>Google Safe Browsing:</strong>{" "}
                  {resultado.fuentes.safe_browsing?.estado === "ok" ? (
                    resultado.fuentes.safe_browsing.datos?.es_maliciosa ? (
                      <span style={{ color: "red", fontWeight: "bold" }}>SITIO AMENAZANTE</span>
                    ) : (
                      <span style={{ color: "green" }}>Limpio</span>
                    )
                  ) : (
                    <span style={{ color: "orange" }}>⚠️ Sin respuesta</span>
                  )}
                </li>

                {/* Antigüedad / WHOIS */}
                <li>
                  <strong>Antigüedad (WHOIS):</strong>{" "}
                  {resultado.fuentes.whois?.estado === "ok" && resultado.fuentes.whois.datos?.dias_antiguedad != null ? (
                    <span style={{ color: "green" }}>
                      {resultado.fuentes.whois.datos.dias_antiguedad} días de antigüedad
                    </span>
                  ) : (
                    <span style={{ color: "orange" }}>⚠️ Sin datos de antigüedad / WHOIS no disponible</span>
                  )}
                </li>

                {/* Certificado SSL */}
                <li>
                  <strong>Certificado SSL:</strong>{" "}
                  {resultado.fuentes.ssl?.estado === "ok" ? (
                    resultado.fuentes.ssl.datos?.valido ? (
                      <span style={{ color: "green" }}>Válido</span>
                    ) : (
                      <span style={{ color: "red", fontWeight: "bold" }}>Inválido o expirado</span>
                    )
                  ) : (
                    <span style={{ color: "orange" }}>⚠️ Sin datos de certificado SSL</span>
                  )}
                </li>
              </ul>
            </div>
          )}

          {resultado.hallazgos_similitud?.length > 0 && (
            <div style={{ marginTop: "15px", textAlign: "left" }}>
              <h3>Direcciones que se parecen a sitios conocidos</h3>
              {resultado.hallazgos_similitud.map((hallazgo, indice) => (
                <p key={indice} style={{ color: "orange" }}>
                  ⚠️ {hallazgo.dominio} se parece a <strong>{hallazgo.referencia}</strong>{" "}
                  ({hallazgo.similitud}% de similitud).
                </p>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ==========================================
// 3. PANTALLA PRINCIPAL
// ==========================================
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