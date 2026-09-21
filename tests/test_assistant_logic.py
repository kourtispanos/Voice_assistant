import subprocess
from datetime import datetime

import pytest

import assistant_logic


def test_fuzzy_contains_exact_match():
    assert assistant_logic.fuzzy_contains("what time is it", "time")


def test_fuzzy_contains_typo_match():
    assert assistant_logic.fuzzy_contains("whats the tyme", "time")


class FixedDateTime(datetime):
    """Lets tests pin `datetime.now()` without touching the real clock."""
    _now = datetime(2026, 1, 1)

    @classmethod
    def now(cls, tz=None):
        return cls._now


@pytest.mark.parametrize("hour,expected_period", [
    (6, "Good morning"),
    (13, "Good afternoon"),
    (18, "Good evening"),
    (23, "Good night"),
    (2, "Good night"),
])
def test_get_greeting_time_of_day(monkeypatch, hour, expected_period):
    FixedDateTime._now = datetime(2026, 1, 1, hour)
    monkeypatch.setattr(assistant_logic, "datetime", FixedDateTime)
    greeting = assistant_logic.get_greeting()
    assert greeting == f"{expected_period}, {assistant_logic.USERNAME}"


def test_handle_command_time():
    response, detail = assistant_logic.handle_command("what time is it")
    assert response.startswith("It's ")
    assert detail is None


def test_handle_command_date():
    response, detail = assistant_logic.handle_command("what's today's date")
    assert response.startswith("Today is ")
    assert detail is None


def test_open_application_unknown():
    assert assistant_logic.open_application("nonexistent") == "I don't know how to open nonexistent"


def test_open_application_success(monkeypatch):
    called = {}

    def fake_popen(path):
        called["path"] = path

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    result = assistant_logic.open_application("notepad")
    assert result == "Opening notepad"
    assert called["path"] == assistant_logic.APP_MAP["notepad"]


def test_open_application_failure(monkeypatch):
    def fake_popen(path):
        raise OSError("boom")

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    result = assistant_logic.open_application("notepad")
    assert result == "I couldn't open notepad"


def test_handle_command_open_routes_to_open_application(monkeypatch):
    monkeypatch.setattr(assistant_logic, "open_application", lambda name: f"Opening {name}")
    response, detail = assistant_logic.handle_command("please open notepad now")
    assert response == "Opening notepad"
    assert detail is None


def test_handle_command_open_unknown_app_asks_which():
    response, detail = assistant_logic.handle_command("open the thing")
    assert response == "Which application should I open?"
    assert detail is None


def test_close_application_unknown():
    assert assistant_logic.close_application("nonexistent") == "I don't know how to close nonexistent"


class FakeProcess:
    def __init__(self, name):
        self.info = {"name": name}
        self.killed = False

    def kill(self):
        self.killed = True


def test_close_application_found_and_killed(monkeypatch):
    proc = FakeProcess("notepad.exe")
    monkeypatch.setattr(assistant_logic.psutil, "process_iter", lambda attrs: [proc])
    result = assistant_logic.close_application("notepad")
    assert result == "Closed notepad"
    assert proc.killed


def test_close_application_not_running(monkeypatch):
    monkeypatch.setattr(assistant_logic.psutil, "process_iter", lambda attrs: [])
    result = assistant_logic.close_application("notepad")
    assert result == "notepad doesn't seem to be open"


def test_run_network_scan_no_risks(monkeypatch):
    fake_report = {
        "devices": [
            {"ip": "192.168.1.2", "open_ports": []},
        ]
    }
    monkeypatch.setattr(assistant_logic, "run_full_scan", lambda: fake_report)
    spoken, detail = assistant_logic.run_network_scan()
    assert "Found 1 devices" in spoken
    assert "No major risks" in spoken
    assert "No major risks" in detail


def test_run_network_scan_with_risks(monkeypatch):
    fake_report = {
        "devices": [
            {"ip": "192.168.1.2", "open_ports": [
                {"port": 445, "service": "SMB", "risk": "SMB has a history..."},
            ]},
            {"ip": "192.168.1.3", "open_ports": []},
        ]
    }
    monkeypatch.setattr(assistant_logic, "run_full_scan", lambda: fake_report)
    spoken, detail = assistant_logic.run_network_scan()
    assert "Found 2 devices" in spoken
    assert "1 of them have potentially risky" in spoken
    assert "192.168.1.2" in detail
    assert "SMB" in detail


def test_run_network_scan_failure(monkeypatch):
    def fake_scan():
        raise RuntimeError("no admin rights")

    monkeypatch.setattr(assistant_logic, "run_full_scan", fake_scan)
    spoken, detail = assistant_logic.run_network_scan()
    assert "administrator privileges" in spoken
    assert "no admin rights" in detail


def test_handle_command_routes_scan_keyword(monkeypatch):
    monkeypatch.setattr(assistant_logic, "run_network_scan", lambda: ("scan done", "detail text"))
    response, detail = assistant_logic.handle_command("please scan the network")
    assert response == "scan done"
    assert detail == "detail text"


def test_the_word_network_alone_does_not_start_a_scan(monkeypatch):
    def fail():
        raise AssertionError("scan must not run")

    monkeypatch.setattr(assistant_logic, "run_network_scan", fail)
    monkeypatch.setattr(assistant_logic, "handle_computer_command", lambda lower, orig: None)
    monkeypatch.setattr(assistant_logic.ollama, "chat", lambda model, messages: {"message": {"content": "an answer"}})
    response, detail = assistant_logic.handle_command("what is a neural network")
    assert response == "an answer"


def test_scan_without_a_target_asks_what_to_scan(monkeypatch):
    def fail():
        raise AssertionError("scan must not run")

    monkeypatch.setattr(assistant_logic, "run_network_scan", fail)
    response, detail = assistant_logic.handle_command("scan")
    assert "What should I scan" in response
    assert detail is None


@pytest.mark.parametrize("heard,expected", [
    ("assistant", True),
    ("assistance", True),
    ("hey assistant", True),
    ("", False),
    ("the weather today", False),
])
def test_matches_wake_word(heard, expected):
    assert assistant_logic.matches_wake_word(heard) is expected


def test_handle_command_delegates_to_computer_control(monkeypatch):
    monkeypatch.setattr(assistant_logic, "handle_computer_command", lambda lower, orig: "Scrolled down")
    response, detail = assistant_logic.handle_command("scroll down")
    assert response == "Scrolled down"
    assert detail is None


def test_handle_command_falls_back_to_ollama(monkeypatch):
    monkeypatch.setattr(assistant_logic, "handle_computer_command", lambda lower, orig: None)

    captured = {}

    def fake_chat(model, messages):
        captured["model"] = model
        captured["messages"] = messages
        return {"message": {"content": "a fake reply"}}

    monkeypatch.setattr(assistant_logic.ollama, "chat", fake_chat)
    response, detail = assistant_logic.handle_command("give a random fact")
    assert response == "a fake reply"
    assert detail is None
    assert captured["model"] == assistant_logic.OLLAMA_MODEL
    assert assistant_logic.conversation_history[-1] == {"role": "assistant", "content": "a fake reply"}


def test_conversation_history_is_capped(monkeypatch):
    monkeypatch.setattr(assistant_logic, "handle_computer_command", lambda lower, orig: None)
    monkeypatch.setattr(assistant_logic.ollama, "chat", lambda model, messages: {"message": {"content": "ok"}})

    for i in range(15):
        assistant_logic.handle_command(f"message {i}")

    assert len(assistant_logic.conversation_history) == 20


def test_get_vosk_model_is_lazy_and_cached(monkeypatch):
    calls = []

    class FakeVoskModel:
        def __init__(self, path):
            calls.append(path)

    monkeypatch.setattr(assistant_logic.vosk, "Model", FakeVoskModel)
    monkeypatch.setattr(assistant_logic.os.path, "isdir", lambda p: True)
    assert assistant_logic._vosk_model is None

    first = assistant_logic.get_vosk_model()
    second = assistant_logic.get_vosk_model()

    assert first is second
    assert len(calls) == 1


def test_warm_up_ollama_swallows_errors(monkeypatch):
    def fake_chat(model, messages):
        raise ConnectionError("ollama not running")

    monkeypatch.setattr(assistant_logic.ollama, "chat", fake_chat)
    assistant_logic.warm_up_ollama()  # must not raise


def test_click_on_is_not_hijacked_by_open_command(monkeypatch):
    # "on" fuzzy-matches "open" (0.67), which used to swallow "click on ..."
    monkeypatch.setattr(assistant_logic, "handle_computer_command", lambda lower, orig: "clicked it")
    response, detail = assistant_logic.handle_command("Click on subscribe.")
    assert response == "clicked it"
    assert detail is None


def test_preload_models_loads_all_three(monkeypatch):
    loaded = []
    monkeypatch.setattr(assistant_logic, "get_vosk_model", lambda: loaded.append("vosk"))
    monkeypatch.setattr(assistant_logic, "get_piper_voice", lambda: loaded.append("piper"))
    monkeypatch.setattr(assistant_logic, "get_whisper_model", lambda: loaded.append("whisper"))
    assistant_logic.preload_models()
    assert loaded == ["vosk", "piper", "whisper"]


def test_preload_models_swallows_errors(monkeypatch):
    def boom():
        raise FileNotFoundError("model missing")

    monkeypatch.setattr(assistant_logic, "get_vosk_model", boom)
    assistant_logic.preload_models()  # must not raise


def test_get_vosk_model_missing_folder_gives_clear_error(monkeypatch):
    monkeypatch.setattr(assistant_logic.os.path, "isdir", lambda p: False)
    with pytest.raises(FileNotFoundError, match="Vosk model not found"):
        assistant_logic.get_vosk_model()
