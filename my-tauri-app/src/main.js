const { invoke } = window.__TAURI__.core;

let transcribeFormEl;
let statusMsgEl;
let resultTextAreaEl;
let fileInputEl;
let modelSelectEl;
let languageSelectEl;
let formatSelectEl;
let submitBtnEl;

async function transcribe(e) {
  e.preventDefault();

  if (fileInputEl.files.length === 0) {
    statusMsgEl.textContent = "Por favor selecciona un archivo.";
    return;
  }

  statusMsgEl.textContent = "Transcribiendo... Por favor espera.";
  resultTextAreaEl.value = "";
  submitBtnEl.disabled = true;

  const file = fileInputEl.files[0];
  const modelSize = modelSelectEl.value;
  const language = languageSelectEl.value;
  const format = formatSelectEl.value;

  const formData = new FormData();
  formData.append("file", file);
  formData.append("model_size", modelSize);
  formData.append("language", language);
  formData.append("beam_size", "3");
  formData.append("out_format", format);

  try {
    const response = await fetch("http://127.0.0.1:8000/transcribe", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Error HTTP: ${response.status}`);
    }

    const data = await response.json();

    if (data.error) {
      statusMsgEl.textContent = "Error: " + data.error;
    } else {
      statusMsgEl.textContent = `Transcripción completada. Idioma detectado: ${data.language || 'N/A'}`;
      resultTextAreaEl.value = data.result;
    }
  } catch (error) {
    statusMsgEl.textContent = "Hubo un error de conexión con el backend: " + error.message;
  } finally {
    submitBtnEl.disabled = false;
  }
}

window.addEventListener("DOMContentLoaded", () => {
  transcribeFormEl = document.querySelector("#transcribe-form");
  statusMsgEl = document.querySelector("#status-msg");
  resultTextAreaEl = document.querySelector("#result");
  fileInputEl = document.querySelector("#file-input");
  modelSelectEl = document.querySelector("#model-select");
  languageSelectEl = document.querySelector("#language-select");
  formatSelectEl = document.querySelector("#format-select");
  submitBtnEl = document.querySelector("#submit-btn");

  transcribeFormEl.addEventListener("submit", transcribe);
});
