import os
import sys
import site

# The GLEW backend's DLL fails to load inside a PyInstaller exe; the SDL2
# backend gets the OpenGL functions from SDL and needs no glew32.dll.
if getattr(sys, "frozen", False):
    os.environ.setdefault("KIVY_GL_BACKEND", "sdl2")

# Fix for PyInstaller: sys.prefix / site.USER_BASE can be None in frozen apps,
# which crashes kivy_deps' internal path-joining logic
if sys.prefix is None:
    sys.prefix = ""
if site.USER_BASE is None:
    site.USER_BASE = ""

from gui import VoiceAssistantApp

if __name__ == "__main__":
    VoiceAssistantApp().run()