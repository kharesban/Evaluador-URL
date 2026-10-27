# Plan vigente de pruebas Jest

Consultar [COBERTURA_AMPLIADA.md](COBERTURA_AMPLIADA.md) para la instalación, matrices y evidencias del alcance final.

La suite ahora contiene 65 casos Jest sobre App.jsx, verLogs.jsx, analisis.js y ResultadoRevision.jsx. Los cuatro archivos se miden incluso si no son importados y exigen al menos 70% por archivo. Solo se excluye main.jsx, que monta React.

Resultados locales: 65 aprobados, 100% de líneas y 98,43% de ramas. El backend se verifica por separado con 106 casos pytest. No se han ejecutado estos cambios todavía en GitHub desde este entorno.
