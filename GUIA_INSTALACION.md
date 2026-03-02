# QualBot — Guía de instalación completa
## Read.ai + Claude + Google Drive + Railway

---

## Visión general

```
Read.ai (ya tenés) → Railway (servidor gratis) → Google Drive (reportes)
```

Tiempo estimado: **45-60 minutos** la primera vez.

---

## PASO 1 — Subir el código a GitHub (10 min)

1. Crear cuenta en **github.com** si no tenés
2. Crear un repositorio nuevo → llamarlo `qualbot`
3. Subir estos archivos:
   - `server.py`
   - `analyzer.py`
   - `report_generator.py`
   - `drive_uploader.py`
   - `requirements.txt`
   - `railway.toml`

**Opción más fácil:** Arrastrar todos los archivos a la pantalla de GitHub después de crear el repo.

---

## PASO 2 — Crear servidor en Railway (10 min)

1. Ir a **railway.app** → Sign up with GitHub
2. Click en **"New Project"**
3. Elegir **"Deploy from GitHub repo"**
4. Seleccionar tu repo `qualbot`
5. Railway detecta automáticamente el `railway.toml` y despliega

Una vez desplegado, Railway te da una URL así:
```
https://qualbot-production-xxxx.up.railway.app
```

**Guardá esa URL**, la necesitás en el Paso 4.

---

## PASO 3 — Configurar Google Drive (15 min)

### 3a. Crear proyecto en Google Cloud

1. Ir a **console.cloud.google.com**
2. Crear proyecto nuevo → llamarlo `qualbot`
3. Buscar "Google Drive API" → Habilitar
4. Ir a **"Credenciales"** → Crear credenciales → **"Cuenta de servicio"**
5. Nombre: `qualbot-drive`
6. Click en la cuenta creada → pestaña **"Claves"** → Agregar clave → JSON
7. Se descarga un archivo `.json` → **guardarlo, no compartirlo**

### 3b. Crear carpeta en Google Drive

1. Abrir **Google Drive**
2. Crear carpeta nueva → llamarla `QualBot Reportes`
3. Click derecho → Compartir → agregar el email de la cuenta de servicio
   (está en el archivo JSON, campo `client_email`)
4. Darle rol **Editor**
5. Copiar el **ID de la carpeta** de la URL:
   ```
   drive.google.com/drive/folders/1ABC123XYZ  ← ese es el ID
   ```

---

## PASO 4 — Configurar variables de entorno en Railway

En Railway → tu proyecto → pestaña **"Variables"**, agregar:

| Variable | Valor |
|---|---|
| `ANTHROPIC_API_KEY` | Tu API key de Anthropic (console.anthropic.com) |
| `GOOGLE_DRIVE_FOLDER_ID` | El ID de la carpeta de Drive del paso 3b |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | El contenido completo del archivo `.json` descargado |

Para `GOOGLE_SERVICE_ACCOUNT_JSON`: abrir el archivo JSON con un editor de texto, copiar TODO el contenido y pegarlo como valor de la variable.

Railway reinicia automáticamente el servidor al guardar las variables.

---

## PASO 5 — Configurar webhook en Read.ai (5 min)

1. Ir a **app.read.ai** → menú de usuario → **Integraciones**
2. Click en **"Webhooks"**
3. Click en **"Add Webhook"**
4. Completar:
   - **Nombre:** `QualBot`
   - **URL:** `https://tu-url.up.railway.app/webhook/readai`
5. Guardar
6. Click en **"Send test"** para verificar que funciona

Si el test devuelve ✅, todo está conectado.

---

## PASO 6 — Probar con una reunión real

1. Crear una reunión de Zoom
2. El bot de Read.ai entra automáticamente (como ya hacía)
3. Al terminar la reunión, Read.ai dispara el webhook
4. En 2-3 minutos aparece el reporte PDF en tu carpeta de Google Drive

---

## Costos

| Servicio | Costo |
|---|---|
| Railway (Hobby plan) | $5/mes |
| Claude API | ~$0.05-0.20 por sesión |
| Google Drive | Gratis |
| Read.ai Pro | Ya lo tenés |
| **Total adicional** | **~$5-10/mes** |

---

## Solución de problemas frecuentes

**El webhook no llega:**
- Verificar que la URL en Read.ai es exactamente `.../webhook/readai`
- En Railway → Logs, ver si hay errores

**Error de Google Drive:**
- Verificar que el email de la service account tiene acceso a la carpeta
- Verificar que el JSON está completo en la variable de entorno

**El PDF no se genera:**
- En Railway → Logs buscar el error específico

---

## ¿Tus socios cómo lo usan?

No tienen que hacer nada técnico. Solo:
1. Crear su reunión de Zoom normalmente
2. Asegurarse de que Read.ai está habilitado en su cuenta (o en la tuya como host)
3. Al terminar, el reporte aparece solo en la carpeta de Drive compartida

---

*QualBot — Desarrollado con Claude · Anthropic*
