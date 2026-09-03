# Transcriptor App (Tauri + Python)

Esta aplicación usa **Tauri 2.0** para la interfaz gráfica y **Python (FastAPI)** como backend para ejecutar `faster-whisper`.

## Requisitos previos

- Node.js (v22+)
- Python 3.12+ (con dependencias instaladas)
- Rust (Cargo)

## Instalación

1. **Backend de Python**
   Asegúrate de instalar las dependencias de Python:
   ```bash
   pip install -r requirements.txt
   ```

2. **Frontend de Tauri**
   Navega a la carpeta de Tauri y descarga las dependencias de node:
   ```bash
   cd my-tauri-app
   npm install
   ```

## Desarrollo / Ejecución

La aplicación de Tauri está configurada para iniciar el servidor de Python local (`server.py`) automáticamente. Para correr la aplicación en modo desarrollo:

```bash
cd my-tauri-app
npm run tauri dev
```

> **Nota**: Si por algún motivo el servidor de Python no se inicia correctamente de forma automática a través de Tauri, puedes lanzarlo manualmente en una terminal aparte antes de ejecutar Tauri:
> ```bash
> python server.py
> ```
