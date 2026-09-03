from faster_whisper import WhisperModel
from datetime import timedelta


class Transcriber:
    def __init__(self, model_size="small", device="cpu", compute_type="int8",
                 cpu_threads=8, num_workers=1):
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=cpu_threads,   # usa los núcleos físicos disponibles
            num_workers=num_workers,   # >1 solo ayuda si procesas varios audios en paralelo
        )

    def transcribe(self, filepath, language=None, beam_size=5, on_segment=None):
        """
        Transcribe un archivo de audio.

        on_segment: callback opcional que se llama por cada segmento generado,
                    recibe (segment, total_duration_seconds). Permite actualizar
                    una barra de progreso en tiempo real, ya que faster-whisper
                    genera los segmentos de forma perezosa (lazy).
        """
        segments, info = self.model.transcribe(
            filepath,
            language=language,
            beam_size=beam_size,
            vad_filter=True,  # filtra silencios, acelera bastante
        )
        result = []
        total_duration = getattr(info, "duration", None)
        for seg in segments:
            result.append(seg)
            if on_segment:
                on_segment(seg, total_duration)
        return result, info

    @staticmethod
    def to_txt(segments) -> str:
        return " ".join(seg.text.strip() for seg in segments)

    @staticmethod
    def to_srt(segments) -> str:
        def ts(seconds):
            td = timedelta(seconds=max(0, seconds))
            ms = int(td.total_seconds() * 1000)
            h, r = divmod(ms, 3600_000)
            m, r = divmod(r, 60_000)
            s, ms = divmod(r, 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        out = []
        for i, seg in enumerate(segments, start=1):
            out.append(f"{i}\n{ts(seg.start)} --> {ts(seg.end)}\n{seg.text.strip()}\n")
        return "\n".join(out)