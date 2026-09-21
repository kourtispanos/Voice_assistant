import threading
from faster_whisper import WhisperModel

WHISPER_MODEL_SIZE = "small"

_whisper_model = None
_whisper_lock = threading.Lock()


def get_whisper_model():
    global _whisper_model
    with _whisper_lock:
        if _whisper_model is None:
            _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
            print("[DEBUG] Whisper loaded on CPU")
    return _whisper_model


def transcribe_audio(audio_data, samplerate):
    import numpy as np
    audio_float = audio_data.astype(np.float32) / 32768.0
    audio_float = audio_float.flatten()

    segments, info = get_whisper_model().transcribe(
        audio_float,
        language="en",
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        condition_on_previous_text=False,
        no_speech_threshold=0.6,
    )
    text = " ".join(segment.text for segment in segments).strip()

    return text if text else None