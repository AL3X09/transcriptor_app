import os
import threading
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from transcriber import Transcriber

app = Flask(__name__)
# Restringir CORS al origen de desarrollo y producción de Tauri
CORS(app, origins=["http://localhost:1420", "tauri://localhost"])

# Variables de estado global para controlar el progreso
state = {
    "is_running": False,
    "files_total": 0,
    "files_done": 0,
    "current_file": "",
    "file_progress": 0.0,
    "logs": [],
    "error": None
}
state_lock = threading.Lock()

# Cache global del modelo para evitar recargas constantes
cached_transcriber = None
cached_model_size = None

def log(message):
    with state_lock:
        state["logs"].append(message)
        print(message)

def update_state(**kwargs):
    with state_lock:
        for k, v in kwargs.items():
            state[k] = v

def run_transcription_job(files, output_dir, model_size, language, beam_size, out_format):
    global cached_transcriber, cached_model_size
    update_state(is_running=True, error=None, logs=[], files_total=len(files), files_done=0, file_progress=0.0)

    # Manejar "Detección automática" (en gui.py se pasaba None)
    if language == "Detección automática":
        language = None

    try:
        if cached_transcriber is None or cached_model_size != model_size:
            log(f"Cargando modelo '{model_size}'...")
            cached_transcriber = Transcriber(model_size=model_size, cpu_threads=8)
            cached_model_size = model_size
            log("Modelo cargado.")
        else:
            log(f"Usando modelo '{model_size}' desde caché.")

        os.makedirs(output_dir, exist_ok=True)

        total = len(files)
        for i, filepath in enumerate(files, start=1):
            filename = os.path.basename(filepath)
            log(f"\n[{i}/{total}] Transcribiendo: {filename} (beam_size={beam_size})")
            update_state(current_file=filename, file_progress=0.0)

            t0 = time.time()

            def on_segment(seg, total_duration, _filename=filename):
                if total_duration:
                    percent = min(100.0, (seg.end / total_duration) * 100)
                    update_state(file_progress=percent)

            try:
                segments, info = cached_transcriber.transcribe(
                    filepath, language=language, beam_size=beam_size, on_segment=on_segment
                )
            except Exception as e:
                log(f"  ERROR en transcripción: {e}")
                update_state(files_done=i)
                continue

            if getattr(info, "language", None):
                log(f"  Idioma detectado: {info.language}")

            base = os.path.splitext(filename)[0]
            out_path = os.path.join(output_dir, f"{base}.{out_format}")

            content = cached_transcriber.to_srt(segments) if out_format == "srt" else cached_transcriber.to_txt(segments)

            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                log(f"  ERROR guardando archivo: {e}")
                update_state(files_done=i)
                continue

            update_state(file_progress=100.0, files_done=i)
            log(f"  Listo en {time.time() - t0:.1f}s -> {out_path}")

        log("\nTranscripción completa.")
    except Exception as e:
        log(f"ERROR GENERAL: {e}")
        update_state(error=str(e))
    finally:
        update_state(is_running=False)

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "ok"})

@app.route('/transcribe', methods=['POST'])
def transcribe():
    data = request.json

    files = data.get("files", [])
    output_dir = data.get("output_dir", "")
    model_size = data.get("model_size", "small")
    language = data.get("language", "Detección automática")
    beam_size = int(data.get("beam_size", 3))
    out_format = data.get("format", "txt")

    if not files:
        return jsonify({"error": "No hay archivos"}), 400

    with state_lock:
        if state["is_running"]:
            return jsonify({"error": "Ya hay una transcripción en curso"}), 400

    threading.Thread(
        target=run_transcription_job,
        args=(files, output_dir, model_size, language, beam_size, out_format),
        daemon=True
    ).start()

    return jsonify({"message": "Job started"})

@app.route('/progress', methods=['GET'])
def progress():
    with state_lock:
        # Hacemos una copia para evitar problemas y limpiamos logs para no reenviarlos todos siempre si quisiéramos,
        # pero es más fácil para el frontend consumirlos y nosotros reiniciarlos cuando inicia el job.
        current_state = dict(state)

    return jsonify(current_state)

if __name__ == '__main__':
    # Usar puerto 5001 local
    app.run(host='127.0.0.1', port=5001)