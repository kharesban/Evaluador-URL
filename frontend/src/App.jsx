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
      // Iniciar el análisis y obtener el UUID de la tarea.
      const respuesta = await fetch("http://localhost:8000/analizar", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url: urlLimpia }),
      });

      if (!respuesta.ok) {
        throw new Error(
          "No se pudo iniciar el análisis. Revisa la URL."
        );
      }

      const tarea = await respuesta.json();

      // Consultar el estado cada segundo.
      for (let intento = 0; intento < 30; intento++) {
        await new Promise((resolve) => setTimeout(resolve, 1000));

        const consulta = await fetch(
          `http://localhost:8000/tareas/${tarea.id}`,
          { cache: "no-store" }
        );

        if (!consulta.ok) {
          throw new Error(
            "No se pudo consultar la tarea. Intenta analizar nuevamente."
          );
        }

        const estado = await consulta.json();

        if (estado.estado === "completado") {
          setResultado(estado.resultado);
          return;
        }

        if (estado.estado === "error") {
          throw new Error(estado.mensaje);
        }

        if (estado.estado !== "en_proceso") {
          throw new Error("El servidor devolvió un estado desconocido.");
        }
      }

      throw new Error(
        "Se alcanzó el límite de consultas. El análisis podría seguir en proceso."
      );
    } catch (error) {
      console.error(error);
      setMensaje(
        error.message || "No fue posible realizar el análisis."
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
          aria-label="URL que deseas analizar"
          placeholder="Ingrese una URL"
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

          <p>Estado de las consultas: {resultado.estado}</p>

          <p>
            Puntuación de riesgo:{" "}
            {resultado.riesgo.puntuacion == null
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