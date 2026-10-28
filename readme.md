# Evaluador de URLs — Escáner de Seguridad y Detección de Phishing

El **Evaluador de URLs** es una plataforma de consulta pasiva diseñada para **analizar enlaces web y explicar de forma clara el origen de su nivel de riesgo**. El sistema no se limita a entregar una calificación numérica; recopila métricas, técnicas(phishing) y arroja una reputación en tiempo real para generar un **desglose explicativo** que detalla *por qué* una URL obtuvo determinada puntuación, dejando la decisión final de interacción **100% en manos del usuario**.

---
## 🔍 ¿Cómo funciona el Evaluador de URLs?

Cuando el usuario ingresa una URL en el panel, el sistema activa un proceso de análisis en tres etapas principales:

1. **Consulta Pasiva de Fuentes (OSINT):** Sin realizar pruebas intrusivas ni ataques al servidor de destino, el backend lanza peticiones asíncronas paralelas a motores de reputación pública (VirusTotal, Google Safe Browsing y PhishTank), consulta la antigüedad del dominio registrado en servidores WHOIS/RDAP y extrae los detalles del certificado SSL/TLS (emisor, validez y coincidencia SNI).
2. **Evaluación de Typosquatting:** Extrae el dominio raíz y los subdominios para compararlos léxicamente mediante el algoritmo **Damerau-Levenshtein (RapidFuzz)** contra una lista de marcas protegidas (como `nu`). Esto detecta variaciones visuales o suplantaciones intencionadas.
3. **Ponderación y Explicación del Resultado:** Un motor de reglas ponderadas procesa todas las fuentes y calcula un puntaje continuo entre **1.000 (sitio confiable/sin alertas)** y **5.000 (sitio de alto riesgo)**. Finalmente, el frontend presenta este puntaje acompañado de un **resumen explicativo** donde detalla cada punto detectado (ej. *"Dominio creado hace menos de 15 días"*, *"Certificado SSL inválido o no coincidente"*, *"Reportado en VirusTotal"*).

## 📌 Arquitectura y Descripción General

El sistema opera bajo un flujo de trabajo asíncrono y distribuido que consolida métricas de reputación externa e inspección técnica de infraestructura.

```text
[ Usuario / Frontend React ] 
       │
       ▼ (Petición HTTP Asíncrona)
[ FastAPI Backend ] 
       ├─► Reputación (VirusTotal, Google Safe Browsing, PhishTank)
       ├─► Typosquatting / Detección de Marca (RapidFuzz / Damerau-Levenshtein)
       ├─► Infraestructura SSL/TLS (SNI + Certifi Validation)
       └─► Antigüedad del Dominio (WHOIS / Fallback RDAP)
       │
       ▼ (Procesamiento Ponderado)
[ Clasificación y Evaluación de Riesgo (1–5) ]

```

---

## Modelo de Clasificación y Puntuación 🔢

El motor de decisión emplea un **modelo ponderado continuo** estructurado en un rango de puntuación de **1 a 5** (donde **1** representa bajo riesgo y **5** un riesgo crítico).

### Ponderación de Indicadores

| Indicador / Módulo | Peso | Descripción / Criterio de Evaluación |
| --- | --- | --- |
| **Reputación Externa** | **40%** | Agregación de señales de VirusTotal, Google Safe Browsing y PhishTank. Un positivo en estas fuentes representa un impacto directo de alto riesgo. |
| **Typosquatting y Marcas** | **25%** | Evaluación de similitud léxica (Damerau-Levenshtein) sobre nombres de dominio y subdominios frente a marcas protegidas (ej. `nu`). |
| **Antigüedad (WHOIS/RDAP)** | **20%** | Evaluación del tiempo de registro del dominio raíz. Los dominios recién creados (< 30–90 días) reciben una mayor penalización de riesgo. |
| **Certificado SSL/TLS** | **15%** | Verificación de validez, caducidad y cadena de confianza (CA/SNI) en el puerto 443. La ausencia o invalidez del certificado suma un impacto de riesgo moderado. |

---

## Rendimiento y Confiabilidad

* **Tiempo Máximo de Respuesta:** Diseñado para completar el ciclo completo en menos de **20 segundos** totales, asegurando un límite individual por módulo de **10 segundos**.
* **Mecanismos de Fallback:** Incorpora llamadas paralelas por protocolo RDAP cuando los servidores de WHOIS convencionales (puerto 43) presentan bloqueos o *timeouts*, garantizando una cobertura de análisis constante entre el **80% y el 100%**.
* **Manejo Transparente de Errores:** Los fallos en certificados SSL o conexiones no tumban el análisis; en su lugar, se registran como estados de evaluación legibles para la interfaz de usuario.

---

## 🛠️ Tecnologías Utilizadas

* **Backend:** Python 3.10+, FastAPI, Uvicorn, Asyncio, HTTPX, RapidFuzz, Certifi.
* **Frontend:** React, React Router, Vite, CSS3.
* **APIs Externas:** Google Safe Browsing API, VirusTotal API, PhishTank API, Servidores RDAP / WHOIS.

---

## ⚙️ Configuración del Entorno de Desarrollo — Backend

Este documento detalla el procedimiento paso a paso para configurar el entorno virtual de Python, seleccionar el intérprete en Visual Studio Code, instalar la extensión Pylance para el soporte de lenguaje y ejecutar el módulo de diagnóstico de URLs (HU 5-8).

### 📋 Requisitos Previos

* **Python:** Versión 3.10 o superior instalada en el sistema.
* **Visual Studio Code:** Editor recomendado.
* **Git Bash:** Consola recomendada para entornos Windows.

---

### Guía de Configuración Paso a Paso

#### 1. Instalación de la Extensión Pylance en VS Code

Para contar con autocompletado, verificación de tipos y resolución correcta de paquetes locales:

1. Abre Visual Studio Code.
2. Ve a la pestaña de extensiones en la barra lateral izquierda (`Ctrl + Shift + X` o `Cmd + Shift + X`).
3. Busca **Pylance** e instálala.
4. *(Opcional)* Asegúrate de tener instalada también la extensión oficial de Python para VS Code.

#### 2. Creación y Activación del Entorno Virtual (venv)

Abre una consola (Git Bash o Terminal) y navega hasta la carpeta del proyecto:

```bash
cd backend

python -m venv venv

source venv/Scripts/activate

```

#### 3. Selección del Intérprete de Python en VS Code

Para vincular las librerías del entorno virtual directamente con VS Code y evitar advertencias como *Import could not be resolved*:

1. Presiona `Ctrl + Shift + P` (o `Cmd + Shift + P` en macOS) para abrir la paleta de comandos.
2. Escribe y selecciona: **Python: Select Interpreter**.
3. Elige la opción que apunta a la carpeta del entorno virtual recién creado: `./venv/Scripts/python.exe` (o la ruta equivalente en tu sistema).
4. Reinicia el servidor de lenguajes ejecutando en la paleta de comandos: **Python: Restart Language Server**.

#### 4. Instalación de Dependencias

Con el entorno virtual activo, instala todas las dependencias requeridas (incluyendo Pydantic, HTTPX, RapidFuzz, Python-WHOIS, Certifi, etc.):

```bash
pip install -r requirements.txt

```

#### 5. Configuración de Variables de Entorno (.env)

Crea un archivo llamado `.env` dentro de la carpeta `backend/` e ingresa las claves de acceso para los servicios externos de reputación (HU 5):

```env
GOOGLE_SAFE_BROWSING_API_KEY=tu_api_key_aqui
VIRUSTOTAL_API_KEY=tu_api_key_aqui

```

---

### 🔑 Nota: Cómo obtener las Claves de API (Google Safe Browsing y VirusTotal)

#### 1. Clave de API para Google Safe Browsing
---

Para interactuar con el servicio de detección de amenazas de Google:

* **Paso 1:** Ve a la consola de desarrolladores: [Google Cloud Console](https://console.cloud.google.com/).
* **Paso 2:** Inicia sesión con tu cuenta de Google y crea un nuevo proyecto (o selecciona uno existente).
* **Paso 3:** En el menú lateral, dirígete a **APIs & Services** > **Library**.
* **Paso 4:** En el buscador, escribe **Safe Browsing API** y selecciona la opción oficial.
* **Paso 5:** Haz clic en el botón **Enable**.
* **Paso 6:** Ve a la pestaña **Credentials**, haz clic en **Create Credentials** y selecciona **API Key**.
* **Paso 7:** Copia el token generado y pégalo en tu archivo `.env` en la variable `GOOGLE_SAFE_BROWSING_API_KEY`.

#### 2. Clave de API para VirusTotal
---

Para consultar la reputación del dominio en múltiples motores antivirus:

* **Paso 1:** Ve al portal oficial: [VirusTotal](https://www.virustotal.com/).
* **Paso 2:** Haz clic en **Sign Up** en la esquina superior derecha y crea una cuenta gratuita (o inicia sesión si ya posees una).
* **Paso 3:** Confirma tu correo electrónico si acabas de registrarte.
* **Paso 4:** Haz clic en tu nombre de usuario/avatar en la esquina superior derecha y selecciona **API key**.
* **Paso 5:** Copia la cadena de texto de tu clave personal (API Key).
* **Paso 6:** Pégala en tu archivo `.env` en la variable `VIRUSTOTAL_API_KEY`.


#### 3. Integración con PhishTank (Sin API Key)
---

El módulo de PhishTank no requiere credenciales de API ni token de autenticación. Funciona realizando peticiones HTTP asíncronas directas a los servicios públicos de comprobación de PhishTank enviando un encabezado User-Agent personalizado para evitar bloqueos por rate-limiting.
