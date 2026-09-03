import os
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from transcriber import Transcriber

app = FastAPI()

# Configurar CORS para permitir que Tauri (que podría servir en localhost en un puerto diferente o como file://) llame a la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mantendremos una instancia simple de Transcriber para reutilizar el modelo
# en memoria si el modelo no cambia.
transcriber_instance = None
current_model_size = None

@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    model_size: str = Form("small"),
    language: str = Form(""),
    beam_size: int = Form(3),
    out_format: str = Form("txt")
):
    global transcriber_instance, current_model_size

    # Manejar el valor vacío de language
    lang = language if language and language != "Detección automática" else None

    if transcriber_instance is None or current_model_size != model_size:
        transcriber_instance = Transcriber(model_size=model_size, cpu_threads=8)
        current_model_size = model_size

    # Guardar el archivo subido en un archivo temporal seguro
    fd, temp_file_path = tempfile.mkstemp(suffix=".audio")
    with os.fdopen(fd, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        segments, info = transcriber_instance.transcribe(
            temp_file_path,
            language=lang,
            beam_size=beam_size
        )

        if out_format == "srt":
            result = transcriber_instance.to_srt(segments)
        else:
            result = transcriber_instance.to_txt(segments)

        return {"result": result, "language": info.language if hasattr(info, "language") else None}
    except Exception as e:
        return {"error": str(e)}
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
