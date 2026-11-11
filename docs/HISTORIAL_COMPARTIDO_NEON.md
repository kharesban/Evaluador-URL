# Historial compartido con Neon y Render

## Arquitectura

- En desarrollo local, si no existe `DATABASE_URL`, el backend usa SQLite (`SQLITE_DB_PATH`, por defecto `backend/evaluaciones.db`).
- En producción, si `DATABASE_URL` contiene una URL `postgres://` o `postgresql://`, el backend usa PostgreSQL mediante `asyncpg`.
- Render ejecuta FastAPI; Neon almacena las evaluaciones compartidas.
- No se implementa autenticación: cualquier persona que pueda abrir la aplicación puede consultar las URL y los reportes de todas las demás personas.

## Configuración en Render

1. Abre el servicio **backend** en Render y entra en **Environment**.
2. Configura `DATABASE_URL` con la cadena PostgreSQL de Neon. Se recomienda copiar la cadena con **Connection pooling** activado.
3. Mantén `GOOGLE_SAFE_BROWSING_API_KEY` y `VIRUSTOTAL_API_KEY` como variables privadas del backend.
4. No configures `DATABASE_URL` en el frontend ni la incluyas en el repositorio.
5. Deja `ENABLE_TASK_CLEANUP` sin definir o con valor `0`. El historial no se elimina automáticamente.
6. Despliega la nueva versión del backend. Al iniciar, FastAPI crea la tabla `tareas` y añade la columna `url` si falta.

El backend elimina de la URL de Neon los parámetros de conexión propios de libpq (`sslmode` y `channel_binding`) y activa TLS en `asyncpg`. El pool usa un máximo de cinco conexiones y desactiva la caché de sentencias preparadas para mejorar la compatibilidad con el endpoint pooler de Neon.

## Configuración local

- Copia `backend/.env.example` como `backend/.env` y completa allí tus claves de API locales.
- No necesitas `DATABASE_URL` para trabajar con SQLite local.
- Para probar contra Neon desde local, define `DATABASE_URL` únicamente en tu entorno local, sin pegarla en el código ni en el chat.

## API del historial compartido

- `GET /tareas?limit=50&offset=0`: lista las evaluaciones más recientes, incluyendo sus resultados y el total disponible.
- `GET /tareas/{tarea_id}`: recupera el estado y el reporte completo de una evaluación.
- `POST /analizar`: crea primero la fila de la evaluación; el backend actualiza el resultado al terminar el worker.

La interfaz carga 50 evaluaciones por página y permite solicitar las siguientes. Los análisis pendientes se vuelven a consultar por su mismo identificador.

## Importar un historial SQLite anterior

Si tienes un archivo local `backend/evaluaciones.db` con revisiones que quieras compartir en Neon, puedes importarlo una sola vez. El proceso no sobrescribe IDs que ya existan.

Desde la raíz del repositorio, define `DATABASE_URL` temporalmente en tu terminal y ejecuta el script. En PowerShell de Windows:

```powershell
$env:DATABASE_URL = "PEGA_AQUI_LA_CADENA_DE_NEON"
python backend/scripts/migrar_sqlite_a_neon.py
Remove-Item Env:DATABASE_URL
```

En Git Bash:

```bash
export DATABASE_URL="PEGA_AQUI_LA_CADENA_DE_NEON"
python backend/scripts/migrar_sqlite_a_neon.py
unset DATABASE_URL
```

Para otra ubicación:

```bash
python backend/scripts/migrar_sqlite_a_neon.py --source /ruta/a/evaluaciones.db
```

El script solo informa cantidades; no imprime URLs, reportes ni credenciales. Conserva una copia del archivo SQLite hasta comprobar que las evaluaciones aparecen en el historial de la aplicación.

## Seguridad y límites

El historial es deliberadamente público para cualquier visitante de la aplicación. No analices URL que contengan tokens, credenciales, identificadores privados ni parámetros confidenciales. Para cambiar a historial privado por usuario, habría que añadir autenticación y autorización antes de publicar.

No subas `.env`, claves de API, `DATABASE_URL` ni archivos SQLite con información sensible a GitHub. El archivo `.gitignore` excluye los archivos `.db` y `.env`.
