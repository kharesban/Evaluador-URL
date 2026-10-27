# QA y DevOps del Sprint 4

La guía vigente es [COBERTURA_AMPLIADA.md](COBERTURA_AMPLIADA.md). Incluye el procedimiento desde la primera etapa fallida, los casos y los límites del alcance.

El pipeline ejecuta QA backend y QA frontend Jest en push a feature, PR hacia main/master y push a main/master. PR y ramas de integración ejecutan además setup/arranque del backend y build del frontend. La protección de main debe exigir los cuatro checks reales.

Las métricas iniciales de 42 casos Jest y 48 pytest se sustituyen por las cifras del alcance ampliado: 65 casos Jest y 106 pytest. Los resultados son locales hasta que se publiquen y se ejecute Actions. Se deben conservar las evidencias reales del PR bloqueado y de la corrección antes de cerrar el informe.

El archivo nuevo 02_cobertura_ampliada_desde_etapa1.patch reemplaza al segundo parche anterior y se aplica después del primer parche. No aplicar ambos segundos parches.
