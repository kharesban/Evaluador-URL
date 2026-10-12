import { useState } from "react";
import { Routes, Route } from "react-router-dom";
import VerLogs from "./verLogs.jsx";
import "./App.css";

export function EvaluadorPrincipal() {
  const [url, setUrl] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [resultado, setResultado] = useState(null);
  const [tiempoEjecucion, setTiempoEjecucion] = useState(null);
  const [cargando, setCargando] = useState(false);

  const analizarURL = async () => {
    setResultado(null);
    setTiempoEjecucion(null);
    setMensaje("");

    const urlLimpia = url.trim();

    if (!/^https?:\/\//i.test(urlLimpia)) {
      setMensaje("La URL debe iniciar con http:// o https://");
      return;
    }

    setCargando(true);

    try {
      const respuesta = await fetch("http://localhost:8000/analizar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: urlLimpia }),
      });

      if (!respuesta.ok) {
        throw new Error("No se pudo iniciar el análisis. Revisa la URL.");
      }

      const tarea = await respuesta.json();

      for (let intento = 0; intento < 30; intento++) {
        await new Promise((resolve) => setTimeout(resolve, 1000));

        const consulta = await fetch(
          `http://localhost:8000/tareas/${tarea.id}`,
          { cache: "no-store" }
        );

        if (!consulta.ok) {
          throw new Error("No se pudo consultar la tarea. Intenta analizar nuevamente.");
        }

        const estado = await consulta.json();

        if (estado.estado === "completado") {
          setResultado(estado.resultado);
          setTiempoEjecucion(estado.tiempo_ejecucion_seg);
          return;
        }

        if (estado.estado === "error") {
          throw new Error(estado.mensaje);
        }

        if (estado.estado !== "en_proceso") {
          throw new Error("El servidor devolvió un estado desconocido.");
        }
      }

      throw new Error("Se alcanzó el límite de consultas.");
    } catch (error) {
      console.error(error);
      setMensaje(error.message || "No fue posible realizar el análisis.");
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="container">
      <h1>Evaluador de URL</h1>

      <div>
        <input
          type="text"
          aria-label="URL que deseas analizar"
          placeholder="Ingrese una URL (https://...)"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={cargando}
        />

        <button onClick={analizarURL} disabled={cargando}>
          {cargando ? "Analizando..." : "Analizar"}
        </button>
      </div>

      {cargando && (
        <div role="status" aria-live="polite">
          <p>Analizando URL, por favor espera...</p>
          <progress aria-label="Análisis en proceso" />
        </div>
      )}

      {mensaje && (
        <p className="error" role="alert">
          {mensaje}
        </p>
      )}

      {resultado && (
        <div className="resultado">
          <h2>Resultado del análisis</h2>

          {tiempoEjecucion && (
            <p><strong>Tiempo de ejecución:</strong> {tiempoEjecucion} segundos</p>
          )}

          {/* CASO 1: DOMINIO INEXISTENTE / NO RESUELVE DNS */}
          {resultado.riesgo?.es_dominio_invalido ? (
            <div style={{
              backgroundColor: "#2a1b0e",
              border: "1px solid #d97706",
              borderRadius: "8px",
              padding: "15px",
              margin: "15px 0",
              textAlign: "center"
            }}>
              <h3 style={{ color: "#f59e0b", marginTop: 0 }}>⚠️ Estado del Dominio</h3>
              <p style={{ fontSize: "16px", margin: "5px 0", color: "#fef3c7" }}>
                {resultado.riesgo.mensaje || "La página no está registrada como un dominio válido o activo."}
              </p>
              <p style={{ fontSize: "12px", color: "#d1d5db" }}>
                No se asignó una puntuación de riesgo debido a que el dominio no resuelve registros DNS.
              </p>
            </div>
          ) : (
            /* CASO 2: DOMINIO VÁLIDO CON EVALUACIÓN DE RIESGO */
            <>
              <p>
                <strong>Puntuación de riesgo:</strong>{" "}
                {resultado.riesgo?.puntuacion == null
                  ? "Sin información suficiente"
                  : `${resultado.riesgo.puntuacion} / 5`}
              </p>

              <p>
                <strong>Cobertura del análisis:</strong> {resultado.riesgo?.cobertura_porcentaje}%
              </p>

              {!resultado.riesgo?.evaluacion_completa && (
                <p className="error">
                  Evaluación incompleta. Indicadores sin datos:{" "}
                  {resultado.riesgo?.indicadores_faltantes?.join(", ")}.
                </p>
              )}

              <p style={{ fontSize: "12px", color: "#666" }}>
                La puntuación va de 1 a 5: 1 representa el menor riesgo y 5 el mayor. 
                Una puntuación de 1 no garantiza seguridad absoluta.
              </p>

              {/* DESGLOSE COMPLETO DE FUENTES ANALIZADAS */}
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

              {/* Hallazgos de Typosquatting */}
              {resultado.hallazgos_similitud?.length > 0 && (
                <div style={{ marginTop: "15px", textAlign: "left" }}>
                  <h3>Hallazgos de similitud (Typosquatting)</h3>
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
      )}
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<EvaluadorPrincipal />} />
      <Route path="/logs" element={<VerLogs />} />
    </Routes>
  );
}