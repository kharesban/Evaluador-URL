# Despliegue continuo de Evaluador URL en Render

## Resultado esperado

GitHub Actions ejecuta los cuatro jobs de QA y build. Si todos aprueban y el push
corresponde a la rama elegida para desplegar, un quinto job publica ese mismo
commit en Render y espera a verlo disponible en backend y frontend.

La preparación inicial y las pruebas locales están hechas. La publicación real
requiere crear los servicios y configurar las variables descritas aquí.

## 1 Aplicar y verificar desde VS Code

Trabajar desde la raíz del repositorio, en la nueva rama feature/cd-render,
partiendo de develop/sprint-4. El parche está basado en
41e99fc2fe7f3b45b963f30602fa3170ab4ce07a. No volver a aplicar los parches de QA antiguos.

Extraer CD_Render_Sprint4.zip fuera del repositorio, en la carpeta padre del
proyecto. Debe quedar esta ruta relativa: ../CD_Render_Sprint4/03_cd_render.patch.

```bash
git branch --show-current
git status --short
git apply --check "../CD_Render_Sprint4/03_cd_render.patch"
git apply "../CD_Render_Sprint4/03_cd_render.patch"
source .venv-qa/Scripts/activate
python -m pytest
npm --prefix frontend ci
npm --prefix frontend run test:ci
npm --prefix frontend run build
git diff --check
```

Si git apply --check produce un error, no aplicar con --reject ni descartar
cambios: revisar primero el mensaje y la versión base. Una salida vacía del
comando --check significa que puede aplicarse.

La API sigue usando localhost si no configuras VITE_API_URL. No hace falta un
archivo .env para ejecutar las pruebas. frontend/.env.example documenta la URL.
Jest recibe una constante local mediante su configuración; Vite sustituye esa
misma constante al compilar, evitando introducir import.meta.env en los módulos
que transforma Babel para las pruebas.

Resultados locales obtenidos durante la preparación:

- Python: 114 casos aprobados (106 existentes y 8 nuevos para salud, CORS y CD).
- Backend: 537/539 sentencias y 158/158 ramas; 99,71 % combinado.
- Jest: 65 casos aprobados, 100 % líneas y 98,43 % ramas.
- Ruff crítico y arranque real de FastAPI: correctos.
- Build con URL HTTPS de ejemplo: correcto y sin API localhost en el bundle.
- La URL de ejemplo se usó solo para comprobar la compilación, no se consultó.

Al aplicar este cambio, actualizar el informe a 179 casos en total y adjuntar
las nuevas evidencias. La cobertura de líneas del backend se redondea a 99,63 %.
No atribuir estos resultados locales a una ejecución de GitHub todavía no hecha.

Después de revisar los cambios:

```bash
git add .
git diff --cached --check
git commit -m "feat: preparar despliegue continuo en Render"
git push -u origin feature/cd-render
```

Si tu rama tiene otro nombre, reemplazarlo en los comandos y la configuración.
En este primer push el job CD Render estará omitido porque aún no está habilitado.
Los cuatro jobs de QA y build deben aprobar.

## 2 Crear primero el backend en Render

Crear una cuenta en https://render.com y seleccionar New > Web Service.
Conectar el repositorio kharesban/Evaluador-URL. Si Render no permite seleccionar
el repositorio, el propietario debe autorizar su acceso. No compartir contraseñas.

| Campo | Valor |
| --- | --- |
| Nombre | Un nombre disponible, por ejemplo evaluador-url-backend |
| Rama inicial | feature/cd-render, o el nombre real de tu rama |
| Root Directory | backend |
| Language o Runtime | Python 3, no Docker |
| Build Command | pip install -r requirements.txt |
| Start Command | python -m uvicorn servidor:app --host 0.0.0.0 --port $PORT --workers 1 |
| Instance Type | Free |
| Auto Deploy | Off |
| Health Check Path | /health |

backend/.python-version indica Python 3.12. No seleccionar un plan de pago.
La creación inicial puede lanzar un despliegue; si no lo hace, usar Manual Deploy
> Deploy latest commit. Esperar el estado Live y guardar la URL HTTPS real.

En Environment, configurar las claves que utiliza la aplicación:

- GOOGLE_SAFE_BROWSING_API_KEY
- VIRUSTOTAL_API_KEY

Usar los valores propios del equipo. No copiarlos al chat, al informe ni al frontend.
Sin esas claves algunos proveedores pueden fallar y el análisis será parcial.

Comprobar en el navegador:

- URL_DEL_BACKEND/health: status ok y el commit publicado.
- URL_DEL_BACKEND/docs: documentación de la API.

No añadir /docs ni /health a la URL base que se configura después.

## 3 Crear el frontend

Seleccionar New > Static Site, con el mismo repositorio y rama inicial.

| Campo | Valor |
| --- | --- |
| Root Directory | frontend |
| Build Command | npm ci && npm run build |
| Publish Directory | dist |
| Auto Deploy | Off |
| Variable NODE_VERSION | 24 |
| Variable SKIP_INSTALL_DEPS | true |
| Variable VITE_API_URL | URL HTTPS real del backend, sin barra final |

No inventar ni reutilizar las URL de ejemplo. El frontend falla deliberadamente
al compilar en Render si falta una URL HTTPS de backend.

En Redirects/Rewrites, añadir:

| Source | Destination | Action |
| --- | --- | --- |
| /* | /index.html | Rewrite |

Esto permite abrir o recargar /logs. En Headers, se puede añadir Cache-Control:
no-store para /deploy-version.json, usado para comprobar el commit publicado.

Desplegar y guardar la URL HTTPS real del frontend. Abrir
URL_DEL_FRONTEND/deploy-version.json: debe contener el SHA publicado.

## 4 Permitir la conexión del frontend en el backend

Volver al servicio backend > Environment y añadir:

| Variable | Valor |
| --- | --- |
| CORS_ORIGINS | URL HTTPS exacta del frontend, sin barra final |

Guardar y desplegar el backend para aplicar el cambio. Si se necesitan varios
orígenes, separarlos con comas. No usar asterisco. Los dos orígenes locales
continúan permitidos para trabajar desde VS Code.

Abrir el frontend y analizar https://example.com. Comprobar que finaliza, que se
muestra la justificación y que no hay errores CORS ni solicitudes a localhost
en las herramientas de red del navegador. Esta es una comprobación manual real:
los tests automatizados de QA continúan usando proveedores simulados.

## 5 Configurar GitHub para habilitar CD

En cada servicio Render > Settings, copiar su Deploy Hook. Es una URL secreta.
No enviarla por chat, ni incluirla en código, capturas o el informe.

Quien tenga permisos suficientes en GitHub debe abrir Settings > Secrets and
variables > Actions y crear estos REPOSITORY SECRETS:

| Secret | Valor |
| --- | --- |
| RENDER_BACKEND_DEPLOY_HOOK | Deploy Hook del backend |
| RENDER_FRONTEND_DEPLOY_HOOK | Deploy Hook del frontend |

En la pestaña Variables, crear estas REPOSITORY VARIABLES, que no son claves:

| Variable | Valor inicial |
| --- | --- |
| RENDER_BACKEND_URL | Origen HTTPS real del backend, sin rutas |
| RENDER_FRONTEND_URL | Origen HTTPS real del frontend, sin rutas |
| RENDER_DEPLOY_BRANCH | feature/cd-render, o el nombre real de tu rama |
| RENDER_CD_ENABLED | true |

No mezclar los nombres de secretos y variables. Las URL públicas no llevan rutas
como /docs, /health o /logs. La variable RENDER_DEPLOY_BRANCH permite validar CD
en esta rama antes de integrar en main; si se omite, el destino predeterminado
es main. Los PR no despliegan y una suite fallida impide que se ejecute CD.

Si no ves Settings, pedir esta configuración al propietario, como ocurrió con
la protección de main. Dejar RENDER_CD_ENABLED sin crear o con valor false hasta
tener todo listo permite seguir ejecutando CI con normalidad.

## 6 Probar el despliegue automático

Con los cuatro jobs ya aprobados y la configuración preparada, producir un nuevo
commit en la rama de despliegue, por ejemplo un cambio real de documentación.
Para probar solo la automatización, se puede crear un commit vacío identificado:

```bash
git commit --allow-empty -m "ci: comprobar despliegue continuo en Render"
git push
```

En GitHub Actions deben pasar los cuatro jobs originales y después CD Render.
El script solicita el SHA exacto con el parámetro ref del hook. Espera hasta diez
minutos por servicio, verifica /health del backend y /deploy-version.json del
frontend y comprueba OpenAPI. El job guarda deploy.json y un resumen.

Si queda omitido: revisar el evento push, el nombre exacto de la rama y
RENDER_CD_ENABLED=true. Si falla: revisar los logs de Render, las URL públicas,
las claves configuradas y los Deploy Hooks; el script no imprime las claves.
Un despliegue fallido no equivale a un test funcional fallido.

## 7 Pasar a main después de la revisión

Integrar la rama siguiendo el flujo del equipo, primero a develop/sprint-4 si
corresponde y luego mediante PR a main. No saltarse la revisión ni la protección.
Cuando main contenga estos archivos, cambiar la rama de ambos servicios Render
a main, mantener Auto Deploy Off y cambiar RENDER_DEPLOY_BRANCH a main.

El push de integración en main debe ejecutar CI y CD. Si ocurrió antes de cambiar
la variable, habilitar la configuración final y producir el siguiente cambio
aprobado en main mediante PR; no atribuir el CD de feature a main.

## 8 Evidencias y alcance

Guardar el gráfico de los cinco jobs aprobados, el resumen del SHA, los servicios
Live de Render con el mismo commit y la aplicación funcionando mediante HTTPS.
La prueba de arranque y de versión no demuestra por sí sola todos los criterios
funcionales: conservar también el caso manual del análisis completo.

En Free, el backend puede suspenderse por inactividad y tarda en despertar.
Abrirlo antes de la demostración. Las tareas y los logs actuales están en memoria,
se pierden al reiniciar y requieren un único worker. Esta configuración sirve
como demostración académica, no aporta persistencia ni escalado de producción.
Este CD es una ampliación opcional; no sustituye el pendiente de proteger main
y documentar un PR bloqueado por una prueba fallida.

## Documentación oficial

- https://render.com/docs/deploy-fastapi
- https://render.com/docs/static-sites
- https://render.com/docs/deploy-hooks
- https://render.com/docs/free
- https://render.com/docs/redirects-rewrites
- https://render.com/docs/python-version
- https://render.com/docs/node-version
- https://vite.dev/config/shared-options.html#define
