import os
import threading
from piper import PiperVoice
import sounddevice as sd
import numpy as np

VOICE_MODEL_PATH = "piper_voices/en_GB-jenny_dioco-medium.onnx"

_piper_voice = None
_piper_lock = threading.Lock()


def get_piper_voice():
    global _piper_voice
    with _piper_lock:
        if _piper_voice is None:
            if not os.path.exists(VOICE_MODEL_PATH):
                raise FileNotFoundError(
                    f"Piper voice not found at {VOICE_MODEL_PATH}. Download the "
                    f".onnx and .onnx.json files into piper_voices/ (README, step 8)."
                )
            _piper_voice = PiperVoice.load(VOICE_MODEL_PATH)
    return _piper_voice


def speak_piper(text):
    """Synthesizes speech using Piper TTS and plays it directly."""
    voice = get_piper_voice()
    audio_chunks = []
    for chunk in voice.synthesize(text):
        audio_chunks.append(np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16))

    if audio_chunks:
        full_audio = np.concatenate(audio_chunks)
        sd.play(full_audio, samplerate=voice.config.sample_rate)
        sd.wait()