# Build: pyinstaller voice_assistant.spec --noconfirm
# BUNDLE_MODELS=0 builds a small exe without the ~3.3 GB of models (for testing).
import glob
import os

from kivy_deps import glew, sdl2
from PyInstaller.utils.hooks import collect_all, collect_data_files

bundle_models = os.environ.get("BUNDLE_MODELS", "1") != "0"
console = os.environ.get("EXE_CONSOLE", "0") == "1"

datas = [("gui.kv", "."), ("Voice.ico", ".")]
binaries = []
hiddenimports = []
datas += collect_data_files("kivy")

if bundle_models:
    datas += [
        ("piper_voices", "piper_voices"),
        ("vosk-model-en-us-0.22", "vosk-model-en-us-0.22"),
    ]
    whisper_dirs = glob.glob(os.path.join(
        os.path.expanduser("~"), ".cache", "huggingface", "hub",
        "models--Systran--faster-whisper-small", "snapshots", "*"))
    if not whisper_dirs:
        raise SystemExit("faster-whisper 'small' not in the Hugging Face cache; run the app once first")
    datas.append((whisper_dirs[0], "whisper-small"))

for pkg in ("faster_whisper", "ctranslate2", "piper", "vosk", "onnxruntime",
            "sounddevice", "_sounddevice_data", "pyautogui", "pytesseract"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "tkinter", "pygame"],
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    # kivy_deps registers <sys.prefix>/share/<dep>/bin as a DLL directory, and
    # inside the exe sys.prefix is the extraction folder, so keep that layout.
    *[Tree(p, prefix=os.path.join("share", os.path.basename(os.path.dirname(p)), "bin"))
      for p in sdl2.dep_bins + glew.dep_bins],
    name="VoiceAssistant",
    icon="Voice.ico",
    console=console,
    upx=False,
    debug=False,
)
