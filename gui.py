import os
import threading
import queue
import time

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from transcriber import Transcriber

AUDIO_EXTENSIONS = (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".wma", ".aac", ".mp4", ".mov")
MODEL_SIZES = ["tiny", "base", "small", "medium", "large-v3", "large-v3-turbo"]
LANGUAGES = {
    "Detección automática": None,
    "Español": "es",
    "Inglés": "en",
    "Portugués": "pt",
    "Francés": "fr",
    "Alemán": "de",
    "Italiano": "it",
}
# Presets de calidad -> beam_size. beam_size más alto = más preciso pero más lento.
QUALITY_PRESETS = {
    "Rápida (beam=1)": 1,
    "Balanceada (beam=3)": 3,
    "Precisa (beam=5)": 5,
}


class TranscriptorApp(tk.Tk):
    def __init__(self, default_output_dir: str, default_model_size: str):
        super().__init__()
        self.title("Transcriptor de Audio a Texto")
        self.geometry("820x680")
        self.minsize(700, 580)

        self.files = []
        self.log_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        self.is_running = False
        self.transcriber = None          # se instancia perezosamente
        self.transcriber_model_size = None

        self._build_ui(default_output_dir, default_model_size)
        self._poll_log_queue()
        self._poll_progress_queue()

    # ------------------------------------------------------------------
    def _build_ui(self, default_output_dir, default_model_size):
        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)

        # --- Archivos ---
        files_frame = ttk.LabelFrame(main, text="1. Archivos de audio", padding=10)
        files_frame.pack(fill="x", pady=(0, 10))

        btns = ttk.Frame(files_frame)
        btns.pack(fill="x")
        ttk.Button(btns, text="Agregar archivo(s)...", command=self.add_files).pack(side="left")
        ttk.Button(btns, text="Quitar seleccionado", command=self.remove_selected).pack(side="left", padx=6)
        ttk.Button(btns, text="Limpiar lista", command=self.clear_files).pack(side="left")

        self.files_listbox = tk.Listbox(files_frame, height=6, selectmode="extended")
        self.files_listbox.pack(fill="x", pady=(8, 0))

        # --- Opciones ---
        opts = ttk.LabelFrame(main, text="2. Opciones", padding=10)
        opts.pack(fill="x", pady=(0, 10))

        ttk.Label(opts, text="Modelo:").grid(row=0, column=0, sticky="w")
        self.model_var = tk.StringVar(value=default_model_size)
        ttk.Combobox(opts, textvariable=self.model_var, values=MODEL_SIZES,
                     state="readonly", width=16).grid(row=0, column=1, sticky="w")

        ttk.Label(opts, text="Idioma:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.lang_var = tk.StringVar(value="Detección automática")
        ttk.Combobox(opts, textvariable=self.lang_var, values=list(LANGUAGES.keys()),
                     state="readonly", width=22).grid(row=1, column=1, sticky="w", pady=(8, 0))

        ttk.Label(opts, text="Calidad:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.quality_var = tk.StringVar(value="Balanceada (beam=3)")
        ttk.Combobox(opts, textvariable=self.quality_var, values=list(QUALITY_PRESETS.keys()),
                     state="readonly", width=22).grid(row=2, column=1, sticky="w", pady=(8, 0))

        ttk.Label(opts, text="Formato:").grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.format_var = tk.StringVar(value="txt")
        fmt_frame = ttk.Frame(opts)
        fmt_frame.grid(row=3, column=1, sticky="w", pady=(8, 0))
        ttk.Radiobutton(fmt_frame, text=".txt", variable=self.format_var, value="txt").pack(side="left")
        ttk.Radiobutton(fmt_frame, text=".srt", variable=self.format_var, value="srt").pack(side="left", padx=(10, 0))

        ttk.Label(opts, text="Carpeta salida:").grid(row=4, column=0, sticky="w", pady=(8, 0))
        out_frame = ttk.Frame(opts)
        out_frame.grid(row=4, column=1, sticky="we", pady=(8, 0))
        self.output_dir_var = tk.StringVar(value=default_output_dir)
        ttk.Entry(out_frame, textvariable=self.output_dir_var, width=45).pack(side="left")
        ttk.Button(out_frame, text="Elegir...", command=self.choose_output_dir).pack(side="left", padx=(6, 0))

        # --- Acción ---
        action = ttk.Frame(main)
        action.pack(fill="x", pady=(0, 4))
        self.start_button = ttk.Button(action, text="Iniciar transcripción", command=self.start_transcription)
        self.start_button.pack(side="left")

        # Progreso general (archivo N de M)
        overall_frame = ttk.Frame(main)
        overall_frame.pack(fill="x", pady=(6, 2))
        ttk.Label(overall_frame, text="Progreso general:").pack(side="left")
        self.overall_progress = ttk.Progressbar(overall_frame, mode="determinate", maximum=100)
        self.overall_progress.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Progreso del archivo actual (en tiempo real, por segmento)
        file_frame = ttk.Frame(main)
        file_frame.pack(fill="x", pady=(2, 10))
        ttk.Label(file_frame, text="Archivo actual:").pack(side="left")
        self.file_progress = ttk.Progressbar(file_frame, mode="determinate", maximum=100)
        self.file_progress.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.file_progress_label = ttk.Label(file_frame, text="0%", width=5)
        self.file_progress_label.pack(side="left", padx=(6, 0))

        # --- Log ---
        log_frame = ttk.LabelFrame(main, text="3. Registro", padding=10)
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, wrap="word", height=14, state="disabled")
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    # ------------------------------------------------------------------
    # Archivos
    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="Selecciona archivos de audio",
            filetypes=[("Audio", " ".join(f"*{e}" for e in AUDIO_EXTENSIONS)), ("Todos", "*.*")],
        )
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                self.files_listbox.insert("end", os.path.basename(p))

    def remove_selected(self):
        for idx in reversed(self.files_listbox.curselection()):
            self.files_listbox.delete(idx)
            del self.files[idx]

    def clear_files(self):
        self.files_listbox.delete(0, "end")
        self.files.clear()

    def choose_output_dir(self):
        d = filedialog.askdirectory(title="Selecciona carpeta de salida")
        if d:
            self.output_dir_var.set(d)

    # ------------------------------------------------------------------
    # Log thread-safe
    def log(self, message: str):
        self.log_queue.put(message)

    def _poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(150, self._poll_log_queue)

    # Progreso del archivo actual, thread-safe (viene del callback on_segment)
    def _poll_progress_queue(self):
        try:
            while True:
                percent = self.progress_queue.get_nowait()
                self.file_progress.configure(value=percent)
                self.file_progress_label.configure(text=f"{percent:.0f}%")
        except queue.Empty:
            pass
        self.after(150, self._poll_progress_queue)

    # ------------------------------------------------------------------
    # Transcripción
    def start_transcription(self):
        if self.is_running:
            messagebox.showinfo("En proceso", "Ya hay una transcripción en curso.")
            return
        if not self.files:
            messagebox.showwarning("Sin archivos", "Agrega al menos un archivo de audio.")
            return

        output_dir = self.output_dir_var.get().strip()
        os.makedirs(output_dir, exist_ok=True)

        self.is_running = True
        self.start_button.configure(state="disabled")
        self.overall_progress.configure(value=0)
        self.file_progress.configure(value=0)
        self.file_progress_label.configure(text="0%")

        threading.Thread(target=self._run_job, daemon=True).start()

    def _run_job(self):
        model_size = self.model_var.get()
        language = LANGUAGES.get(self.lang_var.get())
        beam_size = QUALITY_PRESETS.get(self.quality_var.get(), 3)
        out_format = self.format_var.get()
        output_dir = self.output_dir_var.get().strip()

        # Cachear el modelo: solo recrear si cambia el tamaño elegido
        if self.transcriber is None or self.transcriber_model_size != model_size:
            self.log(f"Cargando modelo '{model_size}'...")
            try:
                self.transcriber = Transcriber(model_size=model_size, cpu_threads=8)
                self.transcriber_model_size = model_size
            except Exception as e:
                self.log(f"ERROR cargando modelo: {e}")
                self._finish_job()
                return
            self.log("Modelo cargado.")

        total = len(self.files)
        for i, filepath in enumerate(self.files, start=1):
            filename = os.path.basename(filepath)
            self.log(f"\n[{i}/{total}] Transcribiendo: {filename} (beam_size={beam_size})")
            self.file_progress.after(0, lambda: self.file_progress.configure(value=0))
            t0 = time.time()

            def on_segment(seg, total_duration, _filename=filename):
                if total_duration:
                    percent = min(100.0, (seg.end / total_duration) * 100)
                    self.progress_queue.put(percent)

            try:
                segments, info = self.transcriber.transcribe(
                    filepath, language=language, beam_size=beam_size, on_segment=on_segment,
                )
            except Exception as e:
                self.log(f"  ERROR: {e}")
                self._update_overall_progress(i, total)
                continue

            if getattr(info, "language", None):
                self.log(f"  Idioma detectado: {info.language}")

            base = os.path.splitext(filename)[0]
            out_path = os.path.join(output_dir, f"{base}.{out_format}")
            content = self.transcriber.to_srt(segments) if out_format == "srt" else self.transcriber.to_txt(segments)

            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                self.log(f"  ERROR guardando archivo: {e}")
                self._update_overall_progress(i, total)
                continue

            self.progress_queue.put(100.0)
            self.log(f"  Listo en {time.time() - t0:.1f}s -> {out_path}")
            self._update_overall_progress(i, total)

        self.log("\nTranscripción completa.")
        self._finish_job()

    def _update_overall_progress(self, current, total):
        percent = (current / total) * 100
        self.overall_progress.after(0, lambda: self.overall_progress.configure(value=percent))

    def _finish_job(self):
        self.is_running = False
        self.start_button.after(0, lambda: self.start_button.configure(state="normal"))