# Corrección de las pruebas de integración del PR 19

## Causa comprobada

La rama feature/hu13_hu14_hu8 sí contenía las pruebas automatizadas. El servidor
cambió el almacenamiento de tareas en memoria por SQLite, pero la fixture de
tests/test_api.py conservó servidor.tareas.clear(). El AttributeError impedía
preparar los nueve casos de API. No era un fallo de Render o del CD.

En frontend se duplicaron ResultadoRevision y Reporte dentro de App.jsx. Los
nuevos enlaces requieren un Router en las pruebas, y Reporte.jsx quedó sin uso
ni cobertura. Las pruebas del componente independiente ya no correspondían al
componente duplicado que utilizaba la aplicación.

## Corrección

- Las pruebas API utilizan un archivo SQLite temporal independiente por caso,
  incluyendo el módulo de limpieza. No tocan la base local ni las APIs reales.
- Se comprueba persistencia entre conexiones y purga de registros mayores a 24 h.
- App reutiliza los componentes ResultadoRevision y Reporte, eliminando las
  definiciones duplicadas y conservando la explicación y el enlace al reporte.
- Reporte consulta tareas mediante el servicio existente, que podrá recibir la
  configuración del CD al integrar las ramas.
- Se conserva la validación de VirusTotal que distingue falta de datos de cero
  detecciones. Un reporte sin puntuación no se etiqueta como normal.
- Las pruebas del evaluador usan MemoryRouter y se añaden pruebas de reporte.
- Se mantiene el mínimo de cobertura del 70 % y se exige también en Reporte.jsx.

## Validación local

- Python: 111 aprobadas; cobertura combinada 99,39 %; SQLite y limpieza 100 %.
- Frontend: 74 aprobadas; líneas 100 %; ramas 98,13 %.
- Ruff crítico, resumen por módulo, arranque FastAPI y build: correctos.
- Estos resultados corresponden al PR 19 corregido, no al CD de otra rama.

## Aplicación

Parche basado en 811a52becb5dd24d6b28772fa5c5d6ef75470ff9 de
feature/hu13_hu14_hu8. No aplicarlo directamente en feature/cd-render ni main.
Extraer Correccion_PR19_QA junto al repositorio, fuera de este.
El responsable del PR puede aplicarlo en su rama actualizada, con árbol limpio:

```bash
git switch feature/hu13_hu14_hu8
git pull --ff-only
git apply --check "../Correccion_PR19_QA/04_corregir_integracion_pr19.patch"
git apply "../Correccion_PR19_QA/04_corregir_integracion_pr19.patch"
python -m pip install -r backend/requirements.txt -r requirements-dev.txt
python -m pytest
python .github/scripts/qa_summary.py
npm --prefix frontend ci
npm --prefix frontend run test:ci
npm --prefix frontend run build
git diff --check
```

Si --check falla, revisar antes de continuar; no forzar ni descartar cambios.
Tras revisar y aprobar las verificaciones locales, guardar el cambio y subirlo
a esa rama para que el PR 19 ejecute nuevamente el pipeline.

## Integración posterior con CD

Esta rama todavía no contiene la configuración CD de feature/cd-render.
Al integrar ambas se deben conservar /health y CORS_ORIGINS del CD, la URL
configurable del frontend, SQLite y las pruebas nuevas. No sustituir un servidor
completo por el otro para resolver conflictos.

SQLite aquí usa un archivo local. Render Free no ofrece almacenamiento local
persistente entre reinicios y despliegues: la publicación de esta versión no
garantizará retener los registros 24 horas. Para esa garantía se necesita una
solución de almacenamiento persistente.

El PR 19 tiene como destino develop/sprint-4. Su fallo no acredita por sí solo
un PR bloqueado hacia main; esa evidencia debe corresponder a la rama protegida.
