from faster_whisper import WhisperModel

# "base" is a good balance of speed/accuracy. Options: tiny, base, small, medium, large-v3
# device="cuda" uses your GPU (much faster); falls back to "cpu" if unavailable
whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
print("[DEBUG] Whisper loaded on CPU")


def transcribe_audio(audio_data, samplerate):
    import numpy as np
    audio_float = audio_data.astype(np.float32) / 32768.0
    audio_float = audio_float.flatten()

    segments, info = whisper_model.transcribe(
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