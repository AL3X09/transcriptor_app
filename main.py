# main.py
import os
from dotenv import load_dotenv

from gui import TranscriptorApp


def main():
    # Carga variables de entorno (rutas por defecto, config, etc.)
    load_dotenv()

    default_output_dir = os.getenv("OUTPUT_DIR", os.path.join(os.path.expanduser("~"), "Transcripciones"))
    default_model_size = os.getenv("DEFAULT_MODEL_SIZE", "small")

    app = TranscriptorApp(
        default_output_dir=default_output_dir,
        default_model_size=default_model_size,
    )
    app.mainloop()


if __name__ == "__main__":
    main()