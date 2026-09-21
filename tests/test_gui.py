import os

import gui


def test_closing_the_window_quits_the_process(monkeypatch):
    calls = []
    app = gui.VoiceAssistantApp()
    monkeypatch.setattr(app, "stop", lambda: calls.append("stop"))
    monkeypatch.setattr(os, "_exit", lambda code: calls.append(("exit", code)))

    app.on_request_close()

    assert calls == ["stop", ("exit", 0)]
