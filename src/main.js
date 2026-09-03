import { Command } from '@tauri-apps/plugin-shell';
import { open } from '@tauri-apps/plugin-dialog';
import { resolveResource } from '@tauri-apps/api/path';

let selectedFiles = [];
let progressInterval = null;

// UI Elements
const filesList = document.getElementById('files-list');
const logContainer = document.getElementById('log-container');
const btnStart = document.getElementById('btn-start');
const inputOutDir = document.getElementById('input-out-dir');
const progOverall = document.getElementById('prog-overall');
const progFile = document.getElementById('prog-file');
const lblFileProg = document.getElementById('lbl-file-prog');

// Inicializar Backend y configuración
async function init() {
  log("Iniciando backend...");
  try {
    const backendPath = await resolveResource('backend/app.py');
    const cmd = Command.create('python', [backendPath]);
    cmd.on('close', data => {
      console.log(`Backend terminó con código ${data.code}`);
    });
    cmd.on('error', error => {
      console.error(`Error en backend: "${error}"`);
    });
    cmd.stdout.on('data', line => {
      console.log(`[Backend]: ${line}`);
      log(`[Backend]: ${line}`);
    });
    cmd.stderr.on('data', line => {
      console.error(`[Backend Err]: ${line}`);
      log(`[Backend Err]: ${line}`);
    });
    await cmd.spawn();
    log("Backend iniciado en puerto 5001.");
  } catch (err) {
    log(`Error al iniciar backend: ${err}`);
  }
}

function log(msg) {
  const line = document.createElement('div');
  line.textContent = msg;
  logContainer.appendChild(line);
  logContainer.scrollTop = logContainer.scrollHeight;
}

// Botones de archivos
document.getElementById('btn-add-files').addEventListener('click', async () => {
  try {
    const files = await open({
      multiple: true,
      filters: [{
        name: 'Audio',
        extensions: ['mp3', 'wav', 'm4a', 'flac', 'ogg', 'wma', 'aac', 'mp4', 'mov']
      }]
    });
    if (files) {
      for (const file of files) {
        if (!selectedFiles.includes(file)) {
          selectedFiles.push(file);
          const li = document.createElement('li');
          // Extraemos nombre simple (última parte del path)
          li.textContent = file.split(/[\\/]/).pop();
          filesList.appendChild(li);
        }
      }
    }
  } catch (e) {
    log(`Error seleccionando archivos: ${e}`);
  }
});

document.getElementById('btn-clear-files').addEventListener('click', () => {
  selectedFiles = [];
  filesList.innerHTML = '';
});

// Botón de directorio
document.getElementById('btn-select-dir').addEventListener('click', async () => {
  try {
    const dir = await open({ directory: true });
    if (dir) {
      inputOutDir.value = dir;
    }
  } catch (e) {
    log(`Error seleccionando carpeta: ${e}`);
  }
});

// Polling de progreso
async function checkProgress() {
  try {
    const res = await fetch('http://localhost:5001/progress');
    const state = await res.json();

    if (state.files_total > 0) {
      const overall = (state.files_done / state.files_total) * 100;
      progOverall.value = overall;
    }

    progFile.value = state.file_progress;
    lblFileProg.textContent = `${Math.round(state.file_progress)}%`;

    // Sincronizar logs desde backend
    // Como el backend va acumulando, mostraremos solo los nuevos.
    if (state.logs && state.logs.length > logContainer.childElementCount) {
      const logs = state.logs;
      logContainer.innerHTML = ''; // Reconstruir para mantenerlo simple.
      for (let msg of logs) {
        const line = document.createElement('div');
        line.textContent = msg;
        logContainer.appendChild(line);
      }
      logContainer.scrollTop = logContainer.scrollHeight;
    }

    if (!state.is_running && btnStart.disabled) {
      btnStart.disabled = false;
      clearInterval(progressInterval);
      if (state.error) {
        log(`Error: ${state.error}`);
      } else {
        log("¡Proceso finalizado!");
      }
    }
  } catch (e) {
    console.error("Error consultando progreso:", e);
  }
}

// Iniciar transcripción
btnStart.addEventListener('click', async () => {
  if (selectedFiles.length === 0) {
    alert("Por favor selecciona al menos un archivo.");
    return;
  }

  const outDir = inputOutDir.value;
  if (!outDir) {
    alert("Por favor selecciona un directorio de salida.");
    return;
  }

  const modelSize = document.getElementById('sel-model').value;
  const lang = document.getElementById('sel-lang').value;
  const quality = document.getElementById('sel-quality').value;
  const format = document.querySelector('input[name="format"]:checked').value;

  btnStart.disabled = true;
  progOverall.value = 0;
  progFile.value = 0;
  lblFileProg.textContent = '0%';
  log("--- Nueva transcripción iniciada ---");

  try {
    const res = await fetch('http://localhost:5001/transcribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        files: selectedFiles,
        output_dir: outDir,
        model_size: modelSize,
        language: lang,
        beam_size: quality,
        format: format
      })
    });

    if (!res.ok) {
      const err = await res.json();
      log(`Error: ${err.error}`);
      btnStart.disabled = false;
      return;
    }

    progressInterval = setInterval(checkProgress, 1000);
  } catch (e) {
    log(`Error iniciando transcripción: ${e}`);
    btnStart.disabled = false;
  }
});

// Arrancar el backend cuando la UI carga
window.addEventListener('DOMContentLoaded', init);
