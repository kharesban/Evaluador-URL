
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { API_URL } from "./servicios/config.js";

export function VerLogs() {
  const [logs, setLogs] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [autoUpdate, setAutoUpdate] = useState(true);
  const [actualizacionManual, setActualizacionManual] = useState(0);

  useEffect(() => {
    let activo = true;

    const obtenerLogs = () => {
      fetch(`${API_URL}/logs`, { cache: "no-store" })
        .then((res) => {
          if (!res.ok) {
            throw new Error("No se pudieron consultar los registros.");
          }
          return res.json();
        })
        .then((data) => {
          if (activo) {
            setLogs(Array.isArray(data.logs) ? data.logs : []);
          }
        })
        .catch((err) => {
          if (activo) {
            console.error("Error consultando logs:", err);
          }
        })
        .finally(() => {
          if (activo) {
            setCargando(false);
          }
        });
    };

    // Primera consulta inmediata al ingresar.
    obtenerLogs();

    const intervalo = autoUpdate
      ? window.setInterval(obtenerLogs, 2000)
      : null;

    return () => {
      activo = false;

      if (intervalo !== null) {
        window.clearInterval(intervalo);
      }
    };
  }, [autoUpdate, actualizacionManual]);

  return (
    <div
      className="contenedor-logs"
      style={{ textAlign: "left", padding: "20px" }}
    >
      <div style={{ marginBottom: "15px" }}>
        <Link
          to="/"
          style={{
            color: "#646cff",
            textDecoration: "none",
            fontWeight: "bold",
          }}
        >
          ← Volver al Evaluador
        </Link>
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h2>📜 Logs y Tiempos de Servidor</h2>

        <div>
          <label style={{ marginRight: "10px" }}>
            <input
              type="checkbox"
              checked={autoUpdate}
              onChange={(e) => setAutoUpdate(e.target.checked)}
            />{" "}
            Auto-actualizar (2s)
          </label>

          <button
            onClick={() =>
              setActualizacionManual((actual) => actual + 1)
            }
          >
            Refrescar
          </button>
        </div>
      </div>

      {cargando ? (
        <p>Cargando registros del servidor...</p>
      ) : (
        <pre
          style={{
            backgroundColor: "#1e1e1e",
            color: "#00ff66",
            padding: "15px",
            borderRadius: "6px",
            maxHeight: "500px",
            overflowY: "auto",
            fontSize: "13px",
            fontFamily: "monospace",
            whiteSpace: "pre-wrap",
            wordBreak: "break-all",
            marginTop: "15px",
          }}
        >
          {logs.length === 0
            ? "No hay registros disponibles."
            : logs.join("\n")}
        </pre>
      )}
    </div>
  );
}

export default VerLogs;
