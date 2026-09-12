import os

import computer_control as cc


def test_scroll_down(monkeypatch):
    calls = []
    monkeypatch.setattr(cc.pyautogui, "scroll", lambda amt: calls.append(amt))
    assert cc.scroll_down() == "Scrolled down"
    assert calls == [-500]


def test_scroll_up(monkeypatch):
    calls = []
    monkeypatch.setattr(cc.pyautogui, "scroll", lambda amt: calls.append(amt))
    assert cc.scroll_up() == "Scrolled up"
    assert calls == [500]


def test_click_here(monkeypatch):
    calls = []
    monkeypatch.setattr(cc.pyautogui, "click", lambda *a, **k: calls.append((a, k)))
    assert cc.click_here() == "Clicked"
    assert calls == [((), {})]


def test_type_text(monkeypatch):
    calls = []
    monkeypatch.setattr(cc.pyautogui, "typewrite", lambda text, interval=0: calls.append(text))
    result = cc.type_text("hello world")
    assert result == "Typed: hello world"
    assert calls == ["hello world"]


def test_take_screenshot(monkeypatch, tmp_path):
    monkeypatch.setattr(os.path, "expanduser", lambda p: str(tmp_path))
    saved = {}
    monkeypatch.setattr(cc.pyautogui, "screenshot", lambda filename: saved.setdefault("filename", filename))
    result = cc.take_screenshot()
    assert result == "Screenshot saved"
    assert saved["filename"].startswith(str(tmp_path))


def test_smart_click_finds_match(monkeypatch):
    fake_data = {
        "text": ["", "Subscribe", "Like"],
        "left": [0, 100, 300],
        "top": [0, 50, 50],
        "width": [0, 80, 40],
        "height": [0, 20, 20],
    }
    monkeypatch.setattr(cc.pyautogui, "screenshot", lambda: object())
    monkeypatch.setattr(cc.pytesseract, "image_to_data", lambda img, output_type: fake_data)
    clicked = {}
    monkeypatch.setattr(cc.pyautogui, "click", lambda x, y: clicked.update(x=x, y=y))

    result = cc.smart_click("subscribe")
    assert "Subscribe" in result
    assert clicked == {"x": 140, "y": 60}


def test_smart_click_no_match(monkeypatch):
    fake_data = {"text": ["Like"], "left": [0], "top": [0], "width": [10], "height": [10]}
    monkeypatch.setattr(cc.pyautogui, "screenshot", lambda: object())
    monkeypatch.setattr(cc.pytesseract, "image_to_data", lambda img, output_type: fake_data)
    result = cc.smart_click("subscribe")
    assert "Couldn't find" in result


def test_handle_computer_command_click_with_target(monkeypatch):
    monkeypatch.setattr(cc, "smart_click", lambda target: f"smart-clicked {target}")
    result = cc.handle_computer_command("click on subscribe now", "click on subscribe now")
    assert result == "smart-clicked subscribe now"


def test_handle_computer_command_click_no_target(monkeypatch):
    monkeypatch.setattr(cc, "click_here", lambda: "clicked-here")
    result = cc.handle_computer_command("click", "click")
    assert result == "clicked-here"


def test_handle_computer_command_scroll_down(monkeypatch):
    monkeypatch.setattr(cc, "scroll_down", lambda: "down")
    assert cc.handle_computer_command("please scroll down", "please scroll down") == "down"


def test_handle_computer_command_scroll_up(monkeypatch):
    monkeypatch.setattr(cc, "scroll_up", lambda: "up")
    assert cc.handle_computer_command("please scroll up", "please scroll up") == "up"


def test_handle_computer_command_screenshot(monkeypatch):
    monkeypatch.setattr(cc, "take_screenshot", lambda: "shot")
    assert cc.handle_computer_command("take a screenshot", "take a screenshot") == "shot"


def test_handle_computer_command_type(monkeypatch):
    monkeypatch.setattr(cc, "type_text", lambda t: f"typed {t}")
    assert cc.handle_computer_command("type hello there", "type hello there") == "typed hello there"


def test_handle_computer_command_unmatched_returns_none():
    assert cc.handle_computer_command("tell me a joke", "tell me a joke") is None
