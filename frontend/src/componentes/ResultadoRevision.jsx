export default function ResultadoRevision({ resultado }) {
  const tiempoEjecucion =
    resultado.tiempo_ejecucion_total_seg ?? resultado.duracion_segundos ?? null;

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
                  {resultado.fuentes.virustotal?.estado === "ok" &&
                  Number.isFinite(resultado.fuentes.virustotal.datos?.maliciosos) &&
                  resultado.fuentes.virustotal.datos.maliciosos >= 0 ? (
                    resultado.fuentes.virustotal.datos?.maliciosos > 0 ? (
                      <span style={{ color: "red", fontWeight: "bold" }}>
                        {resultado.fuentes.virustotal.datos.maliciosos} detecciones maliciosas
                      </span>
                    ) : (
                      <span style={{ color: "green" }}>0 detecciones maliciosas</span>
                    )
                  ) : (
                    <span style={{ color: "orange" }}>⚠️ Sin respuesta o sin datos verificables</span>
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
