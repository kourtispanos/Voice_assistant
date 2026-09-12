import numpy as np

import speech_recognition_module as srm


class FakeSegment:
    def __init__(self, text):
        self.text = text


class FakeWhisperModel:
    def __init__(self, segments):
        self._segments = segments
        self.calls = []

    def transcribe(self, audio, **kwargs):
        self.calls.append((audio, kwargs))
        return self._segments, None


def test_get_whisper_model_is_lazy_and_cached(monkeypatch):
    created = []

    class FakeCtor:
        def __init__(self, size, device, compute_type):
            created.append((size, device, compute_type))

    monkeypatch.setattr(srm, "WhisperModel", FakeCtor)
    assert srm._whisper_model is None

    first = srm.get_whisper_model()
    second = srm.get_whisper_model()

    assert first is second
    assert len(created) == 1


def test_transcribe_audio_joins_segments_and_normalizes(monkeypatch):
    fake_model = FakeWhisperModel([FakeSegment("hello"), FakeSegment("world")])
    monkeypatch.setattr(srm, "get_whisper_model", lambda: fake_model)

    audio = np.array([16384, -16384, 0], dtype=np.int16)
    result = srm.transcribe_audio(audio, samplerate=16000)

    assert result == "hello world"
    assert fake_model.calls[0][1]["language"] == "en"
    passed_audio = fake_model.calls[0][0]
    np.testing.assert_allclose(passed_audio, audio.astype(np.float32) / 32768.0)


def test_transcribe_audio_returns_none_when_no_speech(monkeypatch):
    fake_model = FakeWhisperModel([])
    monkeypatch.setattr(srm, "get_whisper_model", lambda: fake_model)

    audio = np.zeros(10, dtype=np.int16)
    assert srm.transcribe_audio(audio, samplerate=16000) is None
