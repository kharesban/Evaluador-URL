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
