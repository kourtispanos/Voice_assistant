import getpass
import os
import sys

USERNAME = getpass.getuser()
SAMPLERATE = 16000
CHUNK_DURATION = 5

OLLAMA_MODEL = "qwen2.5:7b"
VOSK_MODEL_DIR = "vosk-model-en-us-0.22"


def resource_path(relative_path):
    """Path to a bundled resource: next to the code in dev, inside the
    PyInstaller bundle when frozen."""
    base_path = getattr(sys, "_MEIPASS", None) or os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def data_path(relative_path):
    """Where a model folder lives: next to the installed exe first (the
    installer downloads models there), then inside the bundle, then the
    current directory. Falls back to the first candidate so error messages
    show where the app expected to find it."""
    roots = []
    if getattr(sys, "frozen", False):
        roots.append(os.path.dirname(sys.executable))
    if getattr(sys, "_MEIPASS", None):
        roots.append(sys._MEIPASS)
    roots.append(os.path.abspath("."))
    for root in roots:
        candidate = os.path.join(root, relative_path)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(roots[0], relative_path)
