import numpy as np
import pytest

import voice_output as vo


class FakeChunk:
    def __init__(self, audio_bytes):
        self.audio_int16_bytes = audio_bytes


class FakeConfig:
    sample_rate = 22050


class FakePiperVoice:
    def __init__(self, chunks):
        self._chunks = chunks
        self.config = FakeConfig()

    def synthesize(self, text):
        for c in self._chunks:
            yield c


def test_get_piper_voice_is_lazy_and_cached(monkeypatch):
    created = []

    class FakeCtor:
        @staticmethod
        def load(path):
            created.append(path)
            return FakePiperVoice([])

    monkeypatch.setattr(vo, "PiperVoice", FakeCtor)
    monkeypatch.setattr(vo.os.path, "exists", lambda p: True)
    assert vo._piper_voice is None

    first = vo.get_piper_voice()
    second = vo.get_piper_voice()

    assert first is second
    assert created == [vo.VOICE_MODEL_PATH]


def test_speak_piper_plays_concatenated_audio(monkeypatch):
    chunk1 = FakeChunk(np.array([1, 2], dtype=np.int16).tobytes())
    chunk2 = FakeChunk(np.array([3, 4], dtype=np.int16).tobytes())
    fake_voice = FakePiperVoice([chunk1, chunk2])
    monkeypatch.setattr(vo, "get_piper_voice", lambda: fake_voice)

    played = {}
    monkeypatch.setattr(vo.sd, "play", lambda audio, samplerate: played.update(audio=audio, samplerate=samplerate))
    monkeypatch.setattr(vo.sd, "wait", lambda: played.setdefault("waited", True))

    vo.speak_piper("hello")

    np.testing.assert_array_equal(played["audio"], np.array([1, 2, 3, 4], dtype=np.int16))
    assert played["samplerate"] == 22050
    assert played["waited"] is True


def test_speak_piper_no_audio_does_not_play(monkeypatch):
    fake_voice = FakePiperVoice([])
    monkeypatch.setattr(vo, "get_piper_voice", lambda: fake_voice)

    calls = []
    monkeypatch.setattr(vo.sd, "play", lambda *a, **k: calls.append("play"))
    monkeypatch.setattr(vo.sd, "wait", lambda: calls.append("wait"))

    vo.speak_piper("")
    assert calls == []


def test_get_piper_voice_missing_file_gives_clear_error(monkeypatch):
    monkeypatch.setattr(vo.os.path, "exists", lambda p: False)
    with pytest.raises(FileNotFoundError, match="Piper voice not found"):
        vo.get_piper_voice()
