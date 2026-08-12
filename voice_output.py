from piper import PiperVoice
import sounddevice as sd
import numpy as np

VOICE_MODEL_PATH = "piper_voices/en_GB-jenny_dioco-medium.onnx"

piper_voice = PiperVoice.load(VOICE_MODEL_PATH)


def speak_piper(text):
    """Synthesizes speech using Piper TTS and plays it directly."""
    audio_chunks = []
    for chunk in piper_voice.synthesize(text):
        audio_chunks.append(np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16))

    if audio_chunks:
        full_audio = np.concatenate(audio_chunks)
        sd.play(full_audio, samplerate=piper_voice.config.sample_rate)
        sd.wait()