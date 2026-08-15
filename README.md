<div align="center">

# 🎙️ Voice Assistant

**A fully offline, voice-activated AI assistant for Windows**

Built with Python, Kivy, Whisper, Ollama, and Piper TTS

![status](https://img.shields.io/badge/status-active-brightgreen)
![python](https://img.shields.io/badge/python-3.12-blue)
![platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![license](https://img.shields.io/badge/license-personal-lightgrey)

</div>

---

##  Features

| | |
|---|---|
|  **Wake word activation** | Say *"assistant"* to start a conversation — no button required |
|  **Offline speech recognition** | Powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — no internet, no API costs |
|  **Natural offline voice** | [Piper TTS](https://github.com/rhasspy/piper) neural voice, not a robotic system voice |
|  **Local AI conversation** | Runs on [Ollama](https://ollama.com) — no API key, no subscription |
|  **App control** | *"open chrome"*, *"close steam"* |
|  **Computer control** | Scroll, click, screenshot, type — and click on-screen elements by name using OCR |
|  **Network scanner** | *"scan the network"* — live host discovery + port scan with risk flagging |
|  **Animated waveform UI** | Built with Kivy, reacts visually while speaking |
|  **System tray support** | Runs quietly in the background instead of closing |
|  **Time-aware greeting** | Greets you differently depending on time of day |

---

##  Tech Stack

| Purpose | Library |
|---|---|
| GUI | [Kivy](https://kivy.org) |
| Speech-to-text | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) *(offline)* |
| Text-to-speech | [Piper TTS](https://github.com/rhasspy/piper) *(offline, neural)* |
| AI conversation | [Ollama](https://ollama.com) *(Llama 3.2 / Qwen2.5)* |
| Network scanning | [scapy](https://scapy.net/) |
| Computer control | [PyAutoGUI](https://pyautogui.readthedocs.io/) + [pytesseract](https://github.com/madmaze/pytesseract) *(OCR)* |
| System tray | [pystray](https://pypi.org/project/pystray/) |

---

##  Setup

### 1. Prerequisites

- **Python 3.12** *(Kivy isn't yet stable on newer versions)*
- **[Ollama](https://ollama.com/download)**, with a model pulled:
  ```bash
  ollama pull llama3.2
  ```
- **[Npcap](https://npcap.com/#download)** *(required by scapy for network scanning)* — select **"Install Npcap in WinPcap API-compatible Mode"**
- **[Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)** *(required for "click on ___" commands)*
- A **[Piper voice](https://huggingface.co/rhasspy/piper-voices)** — this project uses `en_GB-jenny_dioco-medium`, placed in a `piper_voices/` folder

### 2. Install dependencies

```bash
python -m venv venv
venv\Scripts\activate
pip install kivy faster-whisper piper-tts sounddevice numpy ollama psutil scapy pystray Pillow pyautogui pytesseract pypiwin32
```

### 3. Configure your applications *(optional)*

Edit `APP_MAP` in `assistant_logic.py`:

```python
APP_MAP = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "notepad": r"C:\Windows\System32\notepad.exe",
    # add your own...
}
```

### 4. Run it

```bash
python main.py
```

>  Network scanning requires **administrator privileges** — right-click your terminal and "Run as administrator" before launching.

---

##  Usage

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

##  Run on startup (Windows)

A `start_assistant.bat` script is included.

1. Right-click `start_assistant.bat` → **Create shortcut**
2. Press `Win + R`, type `shell:startup`, hit Enter
3. Move the shortcut into that folder

---

##  Known Limitations

- **No standalone `.exe` yet** — PyInstaller hits a persistent Kivy/GLEW DLL loading issue in frozen builds, even with Kivy's official hooks. The `.bat` launcher is the current workaround.
- **Wake word detection is basic** — simple keyword matching, not a dedicated wake-word model. Expect occasional false positives/negatives.
- **Network scan requires admin rights**, and fails silently without them.
- **OCR-based clicking** works best on clear, printed text — it can't identify icons or images without accompanying text.
- **No persistent memory between sessions** — conversation context resets on restart.

---

##  Project Structure

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
├── start_assistant.bat              # Startup launcher
├── Voice.ico                        # App icon
├── piper_voices/                    # Piper TTS voice model
└── vosk-model-en-us-0.22/           # Wake word detection model
```

---

<div align="center">

*Personal project — use, fork, or adapt as you like.*

</div>
