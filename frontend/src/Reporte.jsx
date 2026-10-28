import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { consultarEstadoTarea } from "./servicios/analisis.js";

export function Reporte() {
  const { tareaId } = useParams();
  const [tarea, setTarea] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const obtenerReporte = async () => {
      try {
        const data = await consultarEstadoTarea(tareaId);
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
            {puntuacion === "N/A" ? "SIN INFORMACIÓN SUFICIENTE" : puntuacion > 3 ? "ALERTAS DETECTADAS" : "DETERMINACIÓN NORMAL"}
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

export default Reporte;
