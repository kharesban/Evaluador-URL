# Configuración del Entorno de Desarrollo — Backend

Este documento detalla el procedimiento paso a paso para configurar el entorno virtual de Python, seleccionar el intérprete en **Visual Studio Code**, instalar la extensión **Pylance** para el soporte de lenguaje y ejecutar el módulo de diagnóstico de URLs (HU 5-8).

---

## 📋 Requisitos Previos

* **Python**: Versión 3.10 o superior instalada en el sistema.
* **Visual Studio Code**: Editor recomendado.
* **Git Bash**: Consola recomendada para entornos Windows.

---

## Guía de Configuración Paso a Paso

### 1. Instalación de la Extensión Pylance en VS Code

Para contar con autocompletado, verificación de tipos y resolución correcta de paquetes locales:

1. Abre **Visual Studio Code**.
2. Ve a la pestaña de extensiones en la barra lateral izquierda (`Ctrl + Shift + X` o `Cmd + Shift + X`).
3. Busca **Pylance** e instálala.
4. *(Opcional)* Asegúrate de tener instalada también la extensión oficial de **Python** para VS Code.

---

### 2. Creación y Activación del Entorno Virtual (`venv`)

Abre una consola (Git Bash o Terminal) y navega hasta la carpeta del proyecto:

```bash
cd backend
```
```Crear el entorno virtual:
python -m venv venv
```

```Activar el entorno virtual (Git Bash):
source venv/Scripts/activate
```

## 3. Selección del Intérprete de Python en VS Code
Para vincular las librerías del entorno virtual directamente con VS Code y evitar advertencias como Import could not be resolved:

Presiona Ctrl + Shift + P (o Cmd + Shift + P en macOS) para abrir la paleta de comandos.

Escribe y selecciona:  **Python: Select Interpreter.**

Elige la opción que apunta a la carpeta del entorno virtual recién creado: **./venv/Scripts/python.exe**(o la ruta equivalente en tu sistema).

Reinicia el servidor de lenguajes ejecutando en la paleta de comandos: Python: Restart Language Server.

## 4. Instalación de Dependencias
Con el entorno virtual activo, instala todas las dependencias requeridas (incluyendo Pydantic, HTTPX, RapidFuzz, Python-WHOIS, etc.):

pip install -r requirements.txt

## 5. Configuración de Variables de Entorno (.env)
Crea un archivo llamado .env dentro de la carpeta backend/ e ingresa las claves de acceso para los servicios externos de reputación (HU 5):
```
GOOGLE_SAFE_BROWSING_API_KEY=tu_api_key_aqui
VIRUSTOTAL_API_KEY=tu_api_key_aqui
```
## Nota: Cómo obtener las Claves de API (Google Safe Browsing y VirusTotal)

### 1. Clave de API para Google Safe Browsing
Para interactuar con el servicio de detección de amenazas de Google:

* **Paso 1:** Ve a la consola de desarrolladores: [Google Cloud Console](https://console.cloud.google.com/).
* **Paso 2:** Inicia sesión con tu cuenta de Google y crea un nuevo proyecto (o selecciona uno existente).
* **Paso 3:** En el menú lateral, dirígete a **APIs & Services** (APIs y servicios) > **Library** (Biblioteca).
* **Paso 4:** En el buscador, escribe **"Safe Browsing API"** y selecciona la opción oficial.
* **Paso 5:** Haz clic en el botón **Enable** (Habilitar).
* **Paso 6:** Ve a la pestaña **Credentials** (Credenciales), haz clic en **Create Credentials** (Crear credenciales) y selecciona **API Key**.
* **Paso 7:** Copia el token generado y pégalo en tu archivo `.env` en la variable `GOOGLE_SAFE_BROWSING_API_KEY`.

---

### 2. Clave de API para VirusTotal
Para consultar la reputación del dominio en múltiples motores antivirus:

* **Paso 1:** Ve al portal oficial: [VirusTotal](https://www.virustotal.com/).
* **Paso 2:** Haz clic en **Sign Up** (Registrarse) en la esquina superior derecha y crea una cuenta gratuita (o inicia sesión si ya posees una).
* **Paso 3:** Confirma tu correo electrónico si acabas de registrarte.
* **Paso 4:** Haz clic en tu nombre de usuario/avatar en la esquina superior derecha y selecciona **API key**.
* **Paso 5:** Copia la cadena de texto de tu clave personal (**API Key**).
* **Paso 6:** Pégala en tu archivo `.env` en la variable `VIRUSTOTAL_API_KEY`.

