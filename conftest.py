"""Shared pytest fixtures.

Its presence at the project root also makes pytest add this directory to
sys.path, so tests can `import assistant_logic`, `import scanner`, etc.
directly without a src-layout or installed package.
"""
import pytest


@pytest.fixture(autouse=True)
def _reset_module_singletons():
    """The lazy-loaded models and conversation history are module-level
    globals; reset them between tests so state can't leak from one test
    into the next."""
    import assistant_logic
    import speech_recognition_module
    import voice_output

    def reset():
        assistant_logic._vosk_model = None
        assistant_logic.conversation_history = []
        speech_recognition_module._whisper_model = None
        voice_output._piper_voice = None

    reset()
    yield
    reset()
