import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { API_URL } from "./servicios/config.js";

export function VerLogs() {
  const [logs, setLogs] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [autoUpdate, setAutoUpdate] = useState(true);

  const obtenerLogs = async () => {
    try {
      const res = await fetch(`${API_URL}/logs`, { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || []);
      }
    } catch (err) {
      console.error("Error consultando logs:", err);
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    obtenerLogs();
    if (!autoUpdate) return;

    const interval = setInterval(() => {
      obtenerLogs();
    }, 2000);

    return () => clearInterval(interval);
  }, [autoUpdate]);

  return (
    <div className="contenedor-logs" style={{ textAlign: "left", padding: "20px" }}>
      <div style={{ marginBottom: "15px" }}>
        <Link to="/" style={{ color: "#646cff", textDecoration: "none", fontWeight: "bold" }}>
          ← Volver al Evaluador
        </Link>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
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
          <button onClick={obtenerLogs}>Refrescar</button>
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
            marginTop: "15px"
          }}
        >
          {logs.length === 0 ? "No hay registros disponibles." : logs.join("\n")}
        </pre>
      )}
    </div>
  );
}

export default VerLogs;
