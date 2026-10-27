import { describe, expect, test } from '@jest/globals';
import { render, screen } from '@testing-library/react';
import ResultadoRevision from '../src/componentes/ResultadoRevision.jsx';

function resultadoLimpio() {
  return {
    tiempo_ejecucion_total_seg: 2.5,
    riesgo: {
      puntuacion: 1, cobertura_porcentaje: 100, evaluacion_completa: true,
      es_dominio_invalido: false, indicadores_faltantes: [],
      detalle_indicadores: [{
        clave: 'ssl', indicador: 'Certificado SSL/TLS', estado: 'evaluado', impacto: 'Bajo',
        peso: 15, contribucion_ponderada: 0, explicacion: 'El certificado SSL/TLS aparece como válido.',
      }],
    },
    fuentes: {
      phishtank: { estado: 'ok', datos: { es_phishing: false } },
      virustotal: { estado: 'ok', datos: { maliciosos: 0 } },
      safe_browsing: { estado: 'ok', datos: { es_maliciosa: false } },
      whois: { estado: 'ok', datos: { dias_antiguedad: 1000 } },
      ssl: { estado: 'ok', datos: { valido: true } },
    },
    hallazgos_similitud: [],
  };
}

describe('HU18: comprender la justificación de la calificación', () => {
  test('U01: muestra puntuación con tres decimales, cobertura y explicación recibida', () => {
    render(<ResultadoRevision resultado={resultadoLimpio()} />);
    expect(screen.getByText(/1\.000 \/ 5/)).toBeVisible();
    expect(screen.getByText(/100%/)).toBeVisible();
    expect(screen.getByText('El certificado SSL/TLS aparece como válido.')).toBeVisible();
    expect(screen.getByText(/Peso: 15%.*Contribución ponderada: 0/)).toBeVisible();
    expect(screen.getByText(/2.5 segundos/)).toBeVisible();
    expect(screen.queryByText(/Evaluación incompleta/)).not.toBeInTheDocument();
  });

  test('U02: un dominio inválido muestra su explicación y oculta la puntuación', () => {
    render(<ResultadoRevision resultado={{ riesgo: { es_dominio_invalido: true, mensaje: 'Dominio no activo.' } }} />);
    expect(screen.getByRole('status')).toHaveTextContent('Dominio no activo.');
    expect(screen.queryByText('Puntuación de riesgo:')).not.toBeInTheDocument();
  });

  test('U03: un dominio inválido sin mensaje usa la explicación predeterminada', () => {
    render(<ResultadoRevision resultado={{ riesgo: { es_dominio_invalido: true } }} />);
    expect(screen.getByRole('status')).toHaveTextContent('La página no está registrada como un dominio válido o activo.');
  });

  test('U04: un puntaje nulo se presenta como información insuficiente', () => {
    const r = resultadoLimpio(); r.riesgo.puntuacion = null;
    render(<ResultadoRevision resultado={r} />);
    expect(screen.getByText(/Sin información suficiente/)).toBeVisible();
    expect(screen.queryByText(/0\.000 \/ 5/)).not.toBeInTheDocument();
  });

  test('U05: una respuesta sin riesgo no inventa puntuación ni detalles', () => {
    render(<ResultadoRevision resultado={{}} />);
    expect(screen.getByText(/Sin información suficiente/)).toBeVisible();
    expect(screen.queryByRole('heading', { name: '¿Por qué obtuvimos esta calificación?' })).not.toBeInTheDocument();
  });

  test('U06: una evaluación parcial identifica sus indicadores faltantes', () => {
    const r = resultadoLimpio();
    r.riesgo.evaluacion_completa = false; r.riesgo.indicadores_faltantes = ['antiguedad', 'reputacion'];
    render(<ResultadoRevision resultado={r} />);
    expect(screen.getByText(/Evaluación incompleta/)).toHaveTextContent('antiguedad, reputacion');
  });

  test.each([['U07a', 'Alto'], ['U07b', 'Medio'], ['U07c', 'Bajo']])('%s: muestra el impacto %s informado por el backend', (_, impacto) => {
    const r = resultadoLimpio(); r.riesgo.detalle_indicadores[0].impacto = impacto;
    render(<ResultadoRevision resultado={r} />);
    expect(screen.getByText(`Impacto ${impacto}`)).toHaveClass(`impacto--${impacto.toLowerCase()}`);
  });

  test('U08: un indicador sin datos se distingue de un indicador evaluado', () => {
    const r = resultadoLimpio();
    Object.assign(r.riesgo.detalle_indicadores[0], { estado: 'sin_datos', impacto: null, contribucion_ponderada: null });
    render(<ResultadoRevision resultado={r} />);
    expect(screen.getByText('Sin datos')).toHaveClass('impacto--sin-datos');
    expect(screen.queryByText(/Contribución ponderada:/)).not.toBeInTheDocument();
  });

  test('U09: muestra las detecciones positivas de las fuentes y el SSL inválido', () => {
    const r = resultadoLimpio();
    r.fuentes.phishtank.datos.es_phishing = true;
    r.fuentes.virustotal.datos.maliciosos = 3;
    r.fuentes.safe_browsing.datos.es_maliciosa = true;
    r.fuentes.ssl.datos.valido = false;
    r.fuentes.whois.datos.dias_antiguedad = 0;
    render(<ResultadoRevision resultado={r} />);
    expect(screen.getByText(/DETECTADO COMO PHISHING/)).toBeVisible();
    expect(screen.getByText('3 detecciones maliciosas')).toBeVisible();
    expect(screen.getByText('SITIO AMENAZANTE')).toBeVisible();
    expect(screen.getByText('Inválido o expirado')).toBeVisible();
    expect(screen.getByText('0 días de antigüedad')).toBeVisible();
  });

  test('U10: distingue los servicios no disponibles de los servicios limpios', () => {
    const r = resultadoLimpio(); r.fuentes = {};
    render(<ResultadoRevision resultado={r} />);
    expect(screen.getByText(/Servicio no disponible/)).toBeVisible();
    expect(screen.getAllByText(/Sin respuesta/)).toHaveLength(2);
    expect(screen.getByText(/WHOIS no disponible/)).toBeVisible();
    expect(screen.getByText(/Sin datos de certificado SSL/)).toBeVisible();
    expect(screen.queryByText('0 detecciones maliciosas')).not.toBeInTheDocument();
  });

  test('U11: WHOIS exitoso sin antigüedad muestra ausencia de datos', () => {
    const r = resultadoLimpio(); r.fuentes.whois.datos = {};
    render(<ResultadoRevision resultado={r} />);
    expect(screen.getByText(/WHOIS no disponible/)).toBeVisible();
  });

  test('U12: muestra el dominio, la referencia y el porcentaje de similitud', () => {
    const r = resultadoLimpio(); r.hallazgos_similitud = [{ dominio: 'goggle.com', referencia: 'google.com', similitud: 83.33 }];
    render(<ResultadoRevision resultado={r} />);
    expect(screen.getByRole('heading', { name: 'Direcciones que se parecen a sitios conocidos' })).toBeVisible();
    expect(screen.getByText('google.com')).toBeVisible();
    expect(screen.getByText(/83.33% de similitud/)).toHaveTextContent('goggle.com');
  });

  test('U13: usa la duración alternativa y permite un resultado sin fuentes ni hallazgos', () => {
    const r = resultadoLimpio();
    delete r.tiempo_ejecucion_total_seg; r.duracion_segundos = 4;
    delete r.fuentes; delete r.hallazgos_similitud; r.riesgo.detalle_indicadores = [];
    render(<ResultadoRevision resultado={r} />);
    expect(screen.getByText(/4 segundos/)).toBeVisible();
    expect(screen.queryByText('Fuentes analizadas:')).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '¿Por qué obtuvimos esta calificación?' })).not.toBeInTheDocument();
  });

  test('U14: nunca presenta una puntuación mínima como garantía absoluta de seguridad', () => {
    render(<ResultadoRevision resultado={resultadoLimpio()} />);
    expect(screen.getByText(/Una puntuación de 1 no garantiza seguridad absoluta/)).toBeVisible();
  });

  test.each([
    ['U15a', undefined], ['U15b', null], ['U15c', -1], ['U15d', NaN], ['U15e', Infinity],
  ])('%s: sin un conteo válido de VirusTotal (%p) no afirma cero detecciones', (_, conteo) => {
    const r = resultadoLimpio(); r.fuentes.virustotal.datos.maliciosos = conteo;
    render(<ResultadoRevision resultado={r} />);
    expect(screen.queryByText('0 detecciones maliciosas')).not.toBeInTheDocument();
    expect(screen.getByText(/Sin respuesta o sin datos verificables/)).toBeVisible();
  });
});
