import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const frontend = fileURLToPath(new URL('../../frontend/', import.meta.url));
const resultsDir = path.join(frontend, 'qa-results');
const tests = JSON.parse(fs.readFileSync(path.join(resultsDir, 'jest-results.json'), 'utf8'));
const coverage = JSON.parse(fs.readFileSync(path.join(resultsDir, 'coverage/coverage-summary.json'), 'utf8'));
const rows = [
  '## QA frontend con Jest', '',
  `Casos: **${tests.numTotalTests}**. Aprobados: **${tests.numPassedTests}**. Fallidos: **${tests.numFailedTests}**. Omitidos: **${tests.numPendingTests}**.`,
  `Commit: \`${process.env.GITHUB_SHA || 'ejecucion-local'}\`.`, '',
  '| Archivo | Sentencias | Ramas | Funciones | Líneas |',
  '|---|---:|---:|---:|---:|',
];
for (const [name, metricas] of Object.entries(coverage)) {
  const label = name === 'total' ? 'Total del alcance Jest' : path.relative(frontend, name).replaceAll('\\', '/');
  rows.push(`| ${label} | ${metricas.statements.pct}% | ${metricas.branches.pct}% | ${metricas.functions.pct}% | ${metricas.lines.pct}% |`);
}
rows.push('', 'Alcance Jest: App.jsx, verLogs.jsx, servicio de seguimiento y presentación del resultado. Solo se excluye main.jsx, que monta React en el DOM. La puntuación del backend se verifica por separado con pytest. No se promedian coberturas de Python y JavaScript.');
const report = rows.join('\n') + '\n';
fs.writeFileSync(path.join(resultsDir, 'resumen-jest.md'), report);
if (process.env.GITHUB_STEP_SUMMARY) fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, report);
console.log(report);
