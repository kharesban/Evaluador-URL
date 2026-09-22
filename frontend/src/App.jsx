import { useState } from "react";
import "./App.css";

function App() {
  const [url, setUrl] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [resultado, setResultado] = useState(null);
  const [cargando, setCargando] = useState(false);

  const analizarURL = async () => {
    setResultado(null);
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
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url: urlLimpia }),
      });

      const datos = await respuesta.json();

      if (!respuesta.ok) {
        const detalle =
          typeof datos.detail === "string"
            ? datos.detail
            : "No se pudo procesar la URL. Revisa que esté bien escrita.";

        setMensaje(detalle);
        return;
      }

      setResultado(datos);
    } catch (error) {
      console.error(error);
      setMensaje(
        "No fue posible completar el análisis. Comprueba que el backend esté ejecutándose."
      );
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
          placeholder="Ingrese una URL"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />

        <button onClick={analizarURL} disabled={cargando}>
          {cargando ? "Analizando..." : "Analizar"}
        </button>
      </div>

      {mensaje && <p className="error">{mensaje}</p>}

      {resultado && (
        <div className="resultado">
          <h2>Resultado del análisis</h2>

          <p>Estado de las consultas: {resultado.estado}</p>

          <p>
            Puntuación de riesgo:{" "}
            {resultado.riesgo.puntuacion === null
              ? "Sin información suficiente"
              : `${resultado.riesgo.puntuacion}/5`}
          </p>

          <p>
            Cobertura: {resultado.riesgo.cobertura_porcentaje}%
          </p>

          {!resultado.riesgo.evaluacion_completa && (
            <p className="error">
              Evaluación incompleta. Indicadores sin datos:{" "}
              {resultado.riesgo.indicadores_faltantes.join(", ")}.
            </p>
          )}

          <p>
            La puntuación va de 1 a 5: 1 representa el menor riesgo
            y 5 el mayor. Una puntuación de 1 no garantiza seguridad.
          </p>

          {resultado.hallazgos_similitud?.length > 0 && (
            <div>
              <h3>Hallazgos de similitud</h3>

              {resultado.hallazgos_similitud.map((hallazgo, indice) => (
                <p key={indice}>
                  {hallazgo.dominio} se parece a {hallazgo.referencia}
                  {" "}({hallazgo.similitud}% de similitud).
                  Posible typosquatting.
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;