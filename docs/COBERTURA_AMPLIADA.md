# Cobertura ampliada - continuación desde la primera etapa

Este documento sustituye las cifras y el alcance de las guías anteriores. Los resultados son locales; faltan las capturas y los enlaces reales de GitHub Actions y del PR. Preparado sobre la versión revisada de develop/sprint-4, commit 06e623ff5b3a2f7b458d8269aa204fd4db34f0a5.

## Punto de partida del usuario

Rama: feature/hu-qa-devops. Carpeta local: Proyecto-Sprint3-Actual.
Ya se aplicó el primer parche y se ejecutaron tres casos Jest: dos aprobados y uno fallido, con cobertura de líneas de 28,20% en el alcance inicial. El fallo identifica que VirusTotal sin conteo se presenta como cero detecciones.

El parche nuevo `02_cobertura_ampliada_desde_etapa1.patch` se aplica DIRECTAMENTE después de esa primera etapa. Incluye la corrección anterior, la suite completa anterior y su ampliación. Reemplaza al segundo parche anterior. No volver a aplicar el primero ni aplicar el segundo anterior antes de este nuevo.

## Aplicación en VS Code / Git Bash

Conservar la evidencia inicial de fallo y bloqueo en el PR antes de actualizarlo. Si todavía no existe el PR, publicar primero la primera etapa y configurar sus checks requeridos, como se indicó en la conversación. El objetivo es registrar primero un fallo real y después su corrección.

Guardar el parche nuevo junto a los dos anteriores, en la carpeta Proyecto Informatico, un nivel por encima del repositorio.
Desde la raíz Proyecto-Sprint3-Actual:

```bash
git branch --show-current
git status --short
git apply --check "../02_cobertura_ampliada_desde_etapa1.patch"
git apply "../02_cobertura_ampliada_desde_etapa1.patch"
```

Si la terminal todavía está en frontend, ejecutar primero `cd ..`. El check debe terminar sin errores. Si indica conflictos o archivos existentes distintos, conservar los cambios y revisar la salida; no forzar la aplicación. Si ya se aplicó el segundo parche anterior, este parche no corresponde a ese estado: comparar antes de continuar.

### Frontend

```bash
cd frontend
npm ci
npm run test:ci
node ../.github/scripts/jest_summary.mjs
npm run build
cd ..
```

### Backend en Windows / Git Bash

Crear un entorno dedicado si aún no existe y usar Python 3.12:

```bash
python -m venv .venv-qa
source .venv-qa/Scripts/activate
python -m pip install -r backend/requirements.txt -r requirements-dev.txt
python -m pip check
python -m pytest
python .github/scripts/qa_summary.py
python -m ruff check backend tests .github/scripts --select E9,F63,F7,F82
python .github/scripts/smoke_backend.py
```

En Linux/macOS, la activación es `source .venv-qa/bin/activate`. Seleccionar `.venv-qa` en Python: Select Interpreter de VS Code para que el editor reconozca pytest.

Revisar los cambios y confirmar solo los archivos del proyecto:

```bash
git add .github .coveragerc .gitignore pytest.ini requirements.txt requirements-dev.txt backend tests frontend docs
git diff --cached --stat
git commit -m "test: ampliar cobertura del frontend y backend web"
git push -u origin feature/hu-qa-devops
```

El push actualiza el mismo PR. Esperar los cuatro checks: QA backend, QA frontend Jest, Setup y arranque backend y Build frontend. Revisar que el fallo inicial y el resultado final pertenezcan a commits identificables. Fusionar solo después de la revisión del equipo. Capturar también el CI por push a main.

## Alcance frontend

Jest incluye todos los archivos .js y .jsx de src. Solo se excluye main.jsx, que monta React en el DOM. Se conserva el registro visible de ramas sin ejecutar; no se agregaron comentarios para ocultarlas.

| Archivo | Casos asociados | Qué comprueban |
|---|---:|---|
| src/servicios/analisis.js | 21 | Inicio, ID, errores HTTP/JSON/red, codificación, intervalos, 30 intentos y cancelación. |
| src/componentes/ResultadoRevision.jsx | 21 | Puntaje y explicación, indicadores faltantes, dominio inválido, fuentes y conteos de VirusTotal. |
| src/App.jsx | 16 | Pantalla inicial, validación, ciclo completo, duplicados, errores, historial, cancelación y rutas. |
| src/verLogs.jsx | 7 | Carga, registros vacíos, errores, actualización cada 2 segundos, pausa, refresco y limpieza al desmontar. |

Los tests de App simulan el servicio para aislar la interacción. Los tests de analisis.js comprueban el servicio real con fetch simulado. No se sustituyen ambos niveles a la vez para afirmar que existe cobertura de un servicio que no se ejecuta. Las rutas usan MemoryRouter y los componentes reales.

## Alcance backend

Coverage recorre backend e incluye archivos no ejecutados. Se excluyen los antiguos scripts manuales backend/main.py y backend/prueba_hu10.py, las carpetas de entornos virtuales y el bloque de uso CLI del worker. El entrypoint web backend/servidor.py sí se mide.

| Archivo de pruebas | Casos | Qué comprueban |
|---|---:|---|
| test_clasificacion.py | 24 | Pesos, límites, datos faltantes y coherencia de la explicación. |
| test_similitud.py | 12 | Dominios oficiales, variaciones y uso de marcas. |
| test_validacion_url.py | 12 | Sintaxis, DNS simulado y señales léxicas. |
| test_api.py | 9 | API real con TestClient: 202, 422, 404, resultado, error del worker, registros y OpenAPI. |
| test_gestor_fuentes.py | 13 | Fuentes async/sync, timeout, excepción, normalización y consolidación completa/parcial/sin resultados. |
| test_worker.py | 7 | Orquestación real y cálculo real con entradas de fuentes simuladas, errores y tiempos controlados. |
| test_diagnosticos.py | 29 | Adaptadores Google, VirusTotal, PhishTank, RDAP y SSL con transporte HTTP y sockets simulados. |

Se bloquean las conexiones reales por defecto dentro de pytest. Las respuestas HTTP se simulan con MockTransport. Los certificados y relojes se controlan para que el resultado no dependa de Internet o de la fecha de ejecución.

Los archivos vacíos de api y db aparecen en la medición con cero sentencias. El resumen los etiqueta como 'No aplica'; no acreditan persistencia ni endpoints adicionales implementados. Las pruebas de API verifican los endpoints activos de servidor.py. No se inventaron pruebas para funcionalidades que no contienen código en la base revisada.

## Resultados locales verificados

| Suite | Casos | Aprobados | Fallidos | Líneas | Ramas |
|---|---:|---:|---:|---:|---:|
| Jest frontend | 65 | 65 | 0 | 100% | 98,43% |
| pytest backend web | 106 | 106 | 0 | 99,62% | 100% |

Backend: 529 de 531 sentencias ejecutadas y 158 de 158 ramas. Cobertura combinada: 99,71%. El archivo de SSL conserva dos líneas sin recorrer correspondientes al fallback de importación de certifi, que es una dependencia instalada. Su cobertura combinada es 95%. No se excluyeron esas líneas para aumentar el porcentaje.

Jest exige >=70% en líneas, ramas, funciones y sentencias, tanto global como por cada uno de sus cuatro archivos. pytest exige cobertura combinada >=70%; el resumen añade una validación >=70% de líneas y ramas por archivo con código. La suite definitiva no tiene casos omitidos ni xfail.

No promediar porcentajes de JavaScript y Python. La aprobación de todos los escenarios seleccionados no significa que se hayan identificado todos los escenarios posibles.

La instalación desde lockfile, el build React, el linter Python y el arranque de FastAPI se validan además de las pruebas. Los resultados de tiempo de los tests no representan rendimiento real de proveedores externos.

## Correcciones respaldadas por pruebas

1. La explicación de antigüedad respeta el umbral de 730 días usado por la fórmula existente.
2. VirusTotal sin un número finito no negativo se muestra sin datos verificables, en vez de cero detecciones.
3. Un HTTP 500 de Google Safe Browsing se trata como error, no como respuesta limpia. El mensaje utiliza el tipo de excepción para evitar incluir una URL con credenciales.
4. Si fallan todos los intentos de PhishTank, se devuelve error de disponibilidad en vez de una consulta limpia. Una respuesta válida sin reporte confirmado sigue teniendo su tratamiento normal.

## Pipeline y evidencias

Se conserva el workflow .github/workflows/ci.yml: push a feature, PR main/master y push main/master, además de develop/sprint-4. Cada evento ejecuta QA Jest y pytest. PR/main ejecutan además setup y build.
Los resúmenes de ambos lenguajes muestran ahora el alcance ampliado. Se conservan artifacts incluso cuando las pruebas fallan. La protección de la rama debe exigir los cuatro checks reales.

Guardar para el informe:

1. Tablero de Sprint 4 con las HU funcionales y el esfuerzo técnico acordado.
2. PR fallido, log de la aserción inicial y cobertura insuficiente.
3. PR bloqueado por checks obligatorios.
4. Ejecución final con QA backend, QA frontend Jest, Setup y arranque backend y Build frontend en verde.
5. Summary y artifacts de ambas suites del mismo commit final.
6. Ejecución por push a main tras la fusión revisada.
7. Enlace al YAML del SHA real y a los runs utilizados.

Los reportes anteriores de 42 casos Jest/48 pytest son del alcance anterior y deben sustituirse por las cifras del run final ampliado. El informe y las diapositivas preliminares requieren actualizarse cuando existan las capturas.

## Límites y avisos pendientes

No se ejecutaron todavía estos cambios en GitHub desde este entorno. Las pruebas de componentes usan jsdom y no sustituyen un recorrido de navegador real. Las integraciones externas se simulan y no demuestran disponibilidad de Google, VirusTotal, PhishTank o servidores RDAP/SSL en producción.

El aviso de tres vulnerabilidades npm observado en el equipo del usuario sigue pendiente de revisar con su npm audit. Este parche no cambia package.json ni package-lock.json frente a la primera etapa y no afirma que esas vulnerabilidades estén corregidas.

La ejecución local de pytest muestra avisos de deprecación de TestClient/httpx y anyio, sin errores de ejecución. No se ocultaron los avisos ni se modificaron versiones solo para suprimirlos.

## Fuentes técnicas

- PDF docente: Requisitos técnicos QA + DevOps, Jorge González R., pp. 1-2.
- Jest, umbrales: https://jestjs.io/docs/configuration
- Jest, temporizadores: https://jestjs.io/docs/timer-mocks
- pytest, monkeypatch: https://docs.pytest.org/en/stable/how-to/monkeypatch.html
- FastAPI, TestClient: https://fastapi.tiangolo.com/tutorial/testing/
