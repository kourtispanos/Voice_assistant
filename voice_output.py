from piper import PiperVoice
import sounddevice as sd
import numpy as np

VOICE_MODEL_PATH = "piper_voices/en_GB-jenny_dioco-medium.onnx"

_piper_voice = None


def get_piper_voice():
    global _piper_voice
    if _piper_voice is None:
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