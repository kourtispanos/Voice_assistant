import sounddevice as sd
import numpy as np
import os
import subprocess
import psutil
import logging
import time
import json
import vosk
import sys
import threading
from datetime import datetime
from config import USERNAME, SAMPLERATE, CHUNK_DURATION, OLLAMA_MODEL, VOSK_MODEL_DIR, data_path
import ollama
from scanner import run_full_scan
from difflib import SequenceMatcher
from computer_control import handle_computer_command
from speech_recognition_module import transcribe_audio, get_whisper_model
from voice_output import speak_piper, get_piper_voice

_PUNCTUATION = ".,!?;:'\"()"

def split_words(text):
    return [w for w in (word.strip(_PUNCTUATION) for word in text.lower().split()) if w]


def fuzzy_contains(text, keyword, threshold=0.65):
    words = text.lower().split()
    for word in words:
        similarity = SequenceMatcher(None, word, keyword).ratio()
        if similarity >= threshold:
            return True
    return False


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


logging.getLogger('comtypes').setLevel(logging.WARNING)
logging.getLogger('comtypes.client._events').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.basicConfig(level=logging.WARNING)

_vosk_model = None
_vosk_lock = threading.Lock()


def get_vosk_model():
    global _vosk_model
    with _vosk_lock:
        if _vosk_model is None:
            model_path = data_path(VOSK_MODEL_DIR)
            if not os.path.isdir(model_path):
                raise FileNotFoundError(
                    f"Vosk model not found at {model_path}. Download "
                    f"{VOSK_MODEL_DIR} from https://alphacephei.com/vosk/models "
                    f"and unzip it into the project folder (README, step 7)."
                )
            _vosk_model = vosk.Model(model_path)
    return _vosk_model


def preload_models():
    """Loads the heavy models in the background so the first wake word /
    reply doesn't pay the load cost. Vosk first, since wake word needs it."""
    try:
        get_vosk_model()
        get_piper_voice()
        get_whisper_model()
        print("[DEBUG] Models preloaded")
    except Exception as e:
        print(f"[DEBUG] Model preload failed: {e}")


def warm_up_ollama():
    try:
        ollama.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": "hi"}])
        print("[DEBUG] Ollama model warmed up successfully")
    except Exception as e:
        print(f"[DEBUG] Ollama warmup failed: {e}")


conversation_history = []


def get_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        period = "Good morning"
    elif 12 <= hour < 17:
        period = "Good afternoon"
    elif 17 <= hour < 21:
        period = "Good evening"
    else:
        period = "Good night"
    return f"{period}, {USERNAME}"


def speak(text, on_start=None, on_end=None):
    if on_start:
        on_start()
    print(f"[DEBUG speak] Speaking: {text}")

    speak_piper(text)

    print("[DEBUG speak] Done")
    if on_end:
        on_end()


def listen_once():
    print(f"[DEBUG] Starting recording: duration={CHUNK_DURATION}, samplerate={SAMPLERATE}")
    recording = sd.rec(int(CHUNK_DURATION * SAMPLERATE), samplerate=SAMPLERATE, channels=1, dtype='int16')
    sd.wait()
    print("[DEBUG] Recording finished, recognizing offline (Whisper)...")

    text = transcribe_audio(recording, SAMPLERATE)

    print(f"[DEBUG] Recognition result: {text}")
    return text

WAKE_WORD = "assistant"
# Vosk often hears "assistance" for "assistant" (ratio ~0.84).
WAKE_WORD_THRESHOLD = 0.8


def matches_wake_word(text):
    return any(
        SequenceMatcher(None, word, WAKE_WORD).ratio() >= WAKE_WORD_THRESHOLD
        for word in split_words(text)
    )


def listen_for_wake_word(chunk_duration=2):
    recording = sd.rec(int(chunk_duration * SAMPLERATE), samplerate=SAMPLERATE, channels=1, dtype='int16')
    sd.wait()

    recognizer = vosk.KaldiRecognizer(get_vosk_model(), SAMPLERATE)
    recognizer.AcceptWaveform(recording.tobytes())
    result = json.loads(recognizer.FinalResult())
    text = result.get("text", "")

    return matches_wake_word(text)


APP_MAP = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "notepad": r"C:\Windows\System32\notepad.exe",
    "tor": r"C:\Users\panos\Desktop\APPS\Tor Browser\Browser\firefox.exe",
    "vm": r"C:\Program Files\Oracle\VirtualBox\VirtualBox.exe",
    "steam": r"C:\Program Files (x86)\Steam.exe",
    "speccy": r"C:\Program Files\Speccy.exe",
}


def open_application(app_name):
    exe_name = APP_MAP.get(app_name.lower())
    if not exe_name:
        return f"I don't know how to open {app_name}"
    try:
        subprocess.Popen(exe_name)
        return f"Opening {app_name}"
    except Exception:
        return f"I couldn't open {app_name}"


def close_application(app_name):
    exe_name = APP_MAP.get(app_name.lower())
    if not exe_name:
        return f"I don't know how to close {app_name}"

    target_filename = os.path.basename(exe_name).lower()
    print(f"[DEBUG close] Target filename: {target_filename}")

    closed = False
    running_processes = []
    for proc in psutil.process_iter(['name']):
        proc_name = proc.info['name']
        if proc_name:
            running_processes.append(proc_name)
        if proc_name and proc_name.lower() == target_filename:
            proc.kill()
            closed = True

    if not closed:
        matches = [p for p in running_processes if app_name.lower() in p.lower()]
        print(f"[DEBUG close] No exact match. Similar running processes: {matches}")

    if closed:
        return f"Closed {app_name}"
    else:
        return f"{app_name} doesn't seem to be open"


def run_network_scan():
    """Returns (spoken_result, written_detail) — written_detail is the fuller
    report text shown in the UI alongside the short spoken summary."""
    try:
        report = run_full_scan()
        num_devices = len(report["devices"])
        risky_devices = [d for d in report["devices"] if any(p["risk"] for p in d["open_ports"])]

        if risky_devices:
            details = "\n".join(
                f"  {d['ip']}: " + ", ".join(p['service'] for p in d['open_ports'] if p['risk'])
                for d in risky_devices
            )
            written_result = (
                f"Found {num_devices} devices.\n"
                f"{len(risky_devices)} device(s) have risky open ports:\n{details}"
            )
            spoken_result = f"Found {num_devices} devices. {len(risky_devices)} of them have potentially risky open ports."
        else:
            written_result = f"Found {num_devices} devices.\nNo major risks detected — network looks safe."
            spoken_result = f"Found {num_devices} devices. No major risks detected."

        return spoken_result, written_result

    except Exception as e:
        return "I couldn't complete the network scan. Make sure I'm running with administrator privileges.", f"Scan failed: {e}"


SCAN_TARGETS = ("network", "networks", "lan", "wifi", "devices", "ports")


def handle_command(text):
    """Returns (spoken_response, detail_text). detail_text is None unless the
    command produced extra written-only detail (e.g. a full scan report)."""
    global conversation_history

    text_lower = text.lower()

    # Checked first: fuzzy matching below is loose enough that e.g. the "on"
    # in "click on subscribe" matches "open" and hijacks the command.
    computer_response = handle_computer_command(text_lower, text)
    if computer_response:
        return computer_response, None

    if fuzzy_contains(text_lower, "time"):
        now = datetime.now().strftime("%H:%M")
        return f"It's {now}", None

    if fuzzy_contains(text_lower, "date") or fuzzy_contains(text_lower, "today"):
        today = datetime.now().strftime("%d/%m/%Y")
        return f"Today is {today}", None

    if fuzzy_contains(text_lower, "open"):
        for app_name in APP_MAP:
            if fuzzy_contains(text_lower, app_name):
                return open_application(app_name), None
        return "Which application should I open?", None

    if fuzzy_contains(text_lower, "close"):
        for app_name in APP_MAP:
            if fuzzy_contains(text_lower, app_name):
                return close_application(app_name), None
        return "Which application should I close?", None

    # A full ARP + port scan is slow, so it needs both a verb and an object:
    # "what is a neural network" must not trigger one.
    words = split_words(text_lower)
    if "scan" in words:
        if any(target in words for target in SCAN_TARGETS):
            return run_network_scan()
        return "What should I scan? Say scan the network.", None

    conversation_history.append({"role": "user", "content": text})
    messages = [
        {"role": "system", "content": "You are a voice assistant. Always answer in EXACTLY ONE short sentence, since your reply will be read aloud. Never use multiple sentences."}
    ] + conversation_history

    response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
    reply = response['message']['content']

    conversation_history.append({"role": "assistant", "content": reply})
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]

    return reply, None