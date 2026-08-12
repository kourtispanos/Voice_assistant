import sys
import site

# Fix for PyInstaller: sys.prefix / site.USER_BASE can be None in frozen apps,
# which crashes kivy_deps' internal path-joining logic
if sys.prefix is None:
    sys.prefix = ""
if site.USER_BASE is None:
    site.USER_BASE = ""

from gui import VoiceAssistantApp

if __name__ == "__main__":
    VoiceAssistantApp().run()