<div align="center">

# Voice Assistant

**A fully offline, voice-activated AI assistant for Windows**

Built with Python, Kivy, Whisper, Vosk, Ollama, and Piper TTS

![status](https://img.shields.io/badge/status-active-brightgreen)
![python](https://img.shields.io/badge/python-3.12-blue)
![platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![license](https://img.shields.io/badge/license-personal-lightgrey)

</div>

---

## Features

| | |
|---|---|
| **Wake word activation** | Say *"assistant"* to start a conversation — no button required |
| **Offline speech recognition** | Wake word via [Vosk](https://alphacephei.com/vosk/), full commands via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — no internet, no API costs |
| **Natural offline voice** | [Piper TTS](https://github.com/rhasspy/piper) neural voice, not a robotic system voice |
| **Local AI conversation** | Runs on [Ollama](https://ollama.com) — no API key, no subscription |
| **App control** | *"open chrome"*, *"close steam"* |
| **Computer control** | Scroll, click, screenshot, type — and click on-screen elements by name using OCR |
| **Network scanner** | *"scan the network"* — live host discovery + port scan with risk flagging |
| **Animated waveform UI** | Built with Kivy, reacts visually while speaking |
| **System tray support** | Runs quietly in the background instead of closing |
| **Time-aware greeting** | Greets you differently depending on time of day |

---

## Tech Stack

| Purpose | Library |
|---|---|
| GUI | [Kivy](https://kivy.org) |
| Wake word detection | [Vosk](https://alphacephei.com/vosk/) *(offline)* |
| Speech-to-text (commands) | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) *(offline)* |
| Text-to-speech | [Piper TTS](https://github.com/rhasspy/piper) *(offline, neural)* |
| AI conversation | [Ollama](https://ollama.com) *(Qwen2.5)* |
| Network scanning | [scapy](https://scapy.net/) |
| Computer control | [PyAutoGUI](https://pyautogui.readthedocs.io/) + [pytesseract](https://github.com/madmaze/pytesseract) *(OCR)* |
| System tray | [pystray](https://pypi.org/project/pystray/) |

---

## Setup

Follow these in order — several steps depend on the previous one (e.g. the app won't even launch without the Vosk model in place).

### 1. Install Python 3.12

Kivy isn't yet stable on newer Python versions, so 3.12 specifically.

- Download from [python.org](https://www.python.org/downloads/release/python-3120/)
- During install, check **"Add python.exe to PATH"**
- Verify:
  ```bash
  python --version
  ```
  should print `Python 3.12.x`

### 2. Create a virtual environment

From the project folder:

```bash
python -m venv venv
venv\Scripts\activate
```

Your prompt should now show `(venv)`. Repeat the `activate` step every time you open a new terminal to run the project.

### 3. Install Python dependencies

```bash
pip install kivy faster-whisper piper-tts vosk sounddevice numpy ollama psutil scapy pystray Pillow pyautogui pytesseract pypiwin32
```

### 4. Install Ollama and pull the model

- Download and install [Ollama](https://ollama.com/download)
- In a terminal, pull the model the assistant actually uses:
  ```bash
  ollama pull qwen2.5:7b
  ```
- Verify it's available:
  ```bash
  ollama list
  ```
  `qwen2.5:7b` should be in the list. Ollama runs as a background service after install, so no need to start it manually.

### 5. Install Npcap (required for network scanning)

- Download from [npcap.com](https://npcap.com/#download)
- During install, check **"Install Npcap in WinPcap API-compatible Mode"** — scapy needs this, plain Npcap mode isn't enough
- No further configuration needed; scapy finds it automatically

### 6. Install Tesseract OCR (required for "click on ___" commands)

- Download the installer from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- Install to the default path (`C:\Program Files\Tesseract-OCR\`)
- If you install it anywhere else, you **must** update the hardcoded path near the top of `computer_control.py`:
  ```python
  pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
  ```
- Verify:
  ```bash
  "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
  ```

### 7. Download the Vosk wake-word model

The app loads this model at startup — it will crash immediately if it's missing.

- Go to [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models) and download **`vosk-model-en-us-0.22`** (~1.8 GB)
- Unzip it into the project root so the folder structure looks like:
  ```
  Voice-assistant/
  └── vosk-model-en-us-0.22/
      ├── am/
      ├── conf/
      ├── graph/
      ├── ivector/
      ├── rescore/
      └── rnnlm/
  ```
  (make sure there isn't an extra nested `vosk-model-en-us-0.22/vosk-model-en-us-0.22/` folder after unzipping — the `am`, `conf`, etc. folders must sit directly inside `vosk-model-en-us-0.22/`)

### 8. Download the Piper voice

- Go to [huggingface.co/rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_GB/jenny_dioco/medium)
- Download both files:
  - `en_GB-jenny_dioco-medium.onnx`
  - `en_GB-jenny_dioco-medium.onnx.json`
- Place both inside a `piper_voices/` folder in the project root

### 9. Configure your applications *(optional)*

Edit `APP_MAP` in `assistant_logic.py` to match apps actually installed on your machine:

```python
APP_MAP = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "notepad": r"C:\Windows\System32\notepad.exe",
    # add your own...
}
```

### 10. Run it

```bash
python main.py
```

> Network scanning requires **administrator privileges** — right-click your terminal (or PowerShell/CMD shortcut) and choose "Run as administrator" before activating the venv and launching. Without it, `"scan the network"` will fail silently.

**Quick troubleshooting:**
- App crashes on startup mentioning `vosk` → the model folder from step 7 is missing or misnamed
- `"I couldn't find '...' on screen"` never works → Tesseract isn't installed, or the path in `computer_control.py` doesn't match your install location
- `"scan the network"` returns nothing / fails → not running as administrator, or Npcap wasn't installed in WinPcap-compatible mode
- No voice output → check that both Piper voice files from step 8 are present in `piper_voices/`
- Ollama replies are slow or errors out → confirm `ollama list` shows `qwen2.5:7b`; a 7B model needs a reasonably capable CPU/GPU

---

## Usage

1. Launch the app — it listens quietly for the wake word (*"assistant"*)
2. Say **"assistant"** to start a conversation
3. Try:
   - `"what time is it"`
   - `"open chrome"` / `"close chrome"`
   - `"scan the network"`
   - `"click on subscribe"` *— finds and clicks on-screen text via OCR*
   - `"scroll down"` / `"take a screenshot"` / `"type hello world"`
4. Say **"stop"** or **"goodbye"**, or press **End Call**, to return to standby
5. Closing the window minimizes it to the system tray — right-click the tray icon to fully quit

---

## Running Tests

The core logic (command routing, app open/close, network scan parsing, model loading) has a pytest suite that mocks out everything external — no microphone, models, Ollama, admin rights, or network access required.

```bash
pip install pytest
pytest
```

---

## Run on startup (Windows)

A `start_assistant.bat` script is included.

1. Right-click `start_assistant.bat` → **Create shortcut**
2. Press `Win + R`, type `shell:startup`, hit Enter
3. Move the shortcut into that folder

---

## Known Limitations

- **No standalone `.exe` yet** — PyInstaller hits a persistent Kivy/GLEW DLL loading issue in frozen builds, even with Kivy's official hooks. The `.bat` launcher is the current workaround.
- **Wake word detection is basic** — it runs a full Vosk transcription on short audio chunks and checks whether the word "assistant" appears in the result, rather than using a dedicated lightweight wake-word engine. Expect occasional false positives/negatives.
- **Network scan requires admin rights**, and fails silently without them.
- **OCR-based clicking** works best on clear, printed text — it can't identify icons or images without accompanying text.
- **No persistent memory between sessions** — conversation context resets on restart.

---

## Project Structure

```
Voice-assistant/
├── main.py                          # Entry point
├── gui.py                           # Kivy UI, waveform animation, tray icon
├── gui.kv                           # Kivy layout definition
├── assistant_logic.py               # Core command routing, AI, app control, network scan
├── speech_recognition_module.py     # Whisper-based speech-to-text
├── voice_output.py                  # Piper-based text-to-speech
├── computer_control.py              # Mouse/keyboard control + OCR-based clicking
├── scanner.py                       # Standalone network scanner module
├── config.py                        # User/audio settings
├── tests/                           # pytest suite (mocks all external dependencies)
├── conftest.py                      # Shared pytest fixtures
├── pytest.ini                       # pytest configuration
├── start_assistant.bat              # Startup launcher
├── Voice.ico                        # App icon
├── piper_voices/                    # Piper TTS voice model (not tracked in git)
└── vosk-model-en-us-0.22/           # Vosk wake-word model (not tracked in git)
```

---

<div align="center">

*Personal project — use, fork, or adapt as you like.*

</div>
