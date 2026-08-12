import sounddevice as sd
import numpy as np
import os
import subprocess
import psutil
import socket
import logging
import time
import json
import vosk
import pyttsx3
import sys
from datetime import datetime
from config import USERNAME, SAMPLERATE, CHUNK_DURATION
import ollama
from scanner import run_full_scan
from difflib import SequenceMatcher
from computer_control import handle_computer_command
from speech_recognition_module import transcribe_audio
from voice_output import speak_piper

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

socket.setdefaulttimeout(30)

vosk_model = vosk.Model(resource_path("vosk-model-en-us-0.22"))

try:
    ollama.chat(model="qwen2.5:7b", messages=[{"role": "user", "content": "hi"}])
    print("[DEBUG] Ollama model warmed up successfully")
except Exception as e:
    print(f"[DEBUG] Ollama warmup failed: {e}")

conversation_history = []
last_scan_result = {"text": ""}


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


def listen_for_wake_word(chunk_duration=2):
    recording = sd.rec(int(chunk_duration * SAMPLERATE), samplerate=SAMPLERATE, channels=1, dtype='int16')
    sd.wait()

    recognizer = vosk.KaldiRecognizer(vosk_model, SAMPLERATE)
    recognizer.AcceptWaveform(recording.tobytes())
    result = json.loads(recognizer.FinalResult())
    text = result.get("text", "").strip().lower()

    if WAKE_WORD in text:
        return True
    return False


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

        last_scan_result["text"] = written_result
        return spoken_result

    except Exception as e:
        last_scan_result["text"] = f"Scan failed: {e}"
        return "I couldn't complete the network scan. Make sure I'm running with administrator privileges."


def handle_command(text):
    global conversation_history

    text_lower = text.lower()

    if fuzzy_contains(text_lower, "time"):
        now = datetime.now().strftime("%H:%M")
        return f"It's {now}"

    if fuzzy_contains(text_lower, "date") or fuzzy_contains(text_lower, "today"):
        today = datetime.now().strftime("%d/%m/%Y")
        return f"Today is {today}"

    if fuzzy_contains(text_lower, "open"):
        for app_name in APP_MAP:
            if fuzzy_contains(text_lower, app_name):
                return open_application(app_name)
        return "Which application should I open?"

    if fuzzy_contains(text_lower, "close"):
        for app_name in APP_MAP:
            if fuzzy_contains(text_lower, app_name):
                return close_application(app_name)
        return "Which application should I close?"

    if "scan" in text_lower.split() or "network" in text_lower:
        return run_network_scan()

    computer_response = handle_computer_command(text_lower, text)
    if computer_response:
        return computer_response

    conversation_history.append({"role": "user", "content": text})
    messages = [
        {"role": "system", "content": "You are a voice assistant. Always answer in EXACTLY ONE short sentence, since your reply will be read aloud. Never use multiple sentences."}
    ] + conversation_history

    response = ollama.chat(model="qwen2.5:7b", messages=messages)
    reply = response['message']['content']

    conversation_history.append({"role": "assistant", "content": reply})
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]

    return reply