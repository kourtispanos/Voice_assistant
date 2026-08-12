import sys
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.graphics import Color, Line
import threading
import math
import time
import traceback
import pystray
from PIL import Image

from assistant_logic import speak, listen_once, handle_command, get_greeting, listen_for_wake_word, last_scan_result


def resource_path(relative_path):
    """Get the absolute path to a resource, works for both dev and PyInstaller exe."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


Builder.load_file(resource_path("gui.kv"))

call_active = False
is_paused = False


class WaveformWidget(Widget):
    amplitude = NumericProperty(3)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.time_offset = 0
        Clock.schedule_interval(self.update_wave, 1 / 30)

    def update_wave(self, dt):
        self.time_offset += dt * 3.5
        self.canvas.clear()

        colors = [
            (0.2, 0.9, 0.8),
            (0.35, 0.55, 1.0),
            (0.75, 0.35, 1.0),
        ]

        with self.canvas:
            for i, base_color in enumerate(colors):
                freq = 0.045 + i * 0.018
                phase = i * 1.8

                points = []
                for x in range(0, int(self.width), 3):
                    y = self.center_y + math.sin(x * freq + self.time_offset + phase) * self.amplitude
                    points.extend([self.x + x, y])

                Color(*base_color, 0.15)
                Line(points=points, width=4)
                Color(*base_color, 0.35)
                Line(points=points, width=2)
                Color(*base_color, 0.9)
                Line(points=points, width=1)

    def set_speaking(self, speaking):
        target = 30 if speaking else 3
        Clock.schedule_once(lambda dt: setattr(self, 'amplitude', target))


class AssistantLayout(BoxLayout):
    def on_kv_post(self, base_widget):
        self.ids.call_btn.bind(on_press=self.toggle_call)
        self.ids.pause_btn.bind(on_press=self.toggle_pause)
        threading.Thread(target=self.wake_word_loop, daemon=True).start()

    def set_status(self, text):
        Clock.schedule_once(lambda dt: setattr(self.ids.status_label, 'text', text))

    def set_result(self, text):
        Clock.schedule_once(lambda dt: setattr(self.ids.result_label, 'text', text))

    def wake_word_loop(self):
        global call_active
        while True:
            if not call_active and not is_paused:
                self.set_status("😴 Say 'assistant' to wake me")
                detected = listen_for_wake_word()
                if detected and not call_active:
                    call_active = True
                    self.ids.call_btn.text = "End Call"
                    self.ids.call_btn.bg_color = (0.75, 0.2, 0.25, 1)
                    self.ids.pause_btn.disabled = False
                    self.call_loop()

    def toggle_call(self, instance):
        global call_active
        if not call_active:
            call_active = True
            self.ids.call_btn.text = "End Call"
            self.ids.call_btn.bg_color = (0.75, 0.2, 0.25, 1)
            self.ids.pause_btn.disabled = False
            threading.Thread(target=self.call_loop, daemon=True).start()
        else:
            call_active = False
            self.ids.call_btn.text = "Start Call"
            self.ids.call_btn.bg_color = (0.16, 0.55, 0.35, 1)
            self.ids.pause_btn.disabled = True
            self.set_status("Ending call...")
            self.ids.waveform.set_speaking(False)

    def toggle_pause(self, instance):
        global is_paused
        is_paused = not is_paused
        if is_paused:
            self.ids.pause_btn.text = "Resume"
            self.set_status("⏸️ Paused")
        else:
            self.ids.pause_btn.text = "Pause"

    def call_loop(self):
        global call_active
        print("[DEBUG] call_loop started")
        greeting = get_greeting()
        print(f"[DEBUG] Greeting: {greeting}")
        self.ids.waveform.set_speaking(True)
        speak(greeting)
        self.ids.waveform.set_speaking(False)

        while call_active:
            if is_paused:
                time.sleep(0.3)
                continue

            try:
                self.set_status("🎙️ Listening...")
                t0 = time.time()
                text = listen_once()
                print(f"[TIMING] listen_once: {time.time() - t0:.2f}s")

                if not call_active:
                    break

                if text:
                    if "stop" in text.lower() or "goodbye" in text.lower():
                        call_active = False
                        break

                    self.set_status("💬 Responding...")

                    t1 = time.time()
                    last_scan_result["text"] = ""
                    response = handle_command(text)
                    print(f"[TIMING] handle_command: {time.time() - t1:.2f}s")

                    if last_scan_result["text"]:
                        self.set_result(f"You: {text}\n\nAssistant: {response}\n\n{last_scan_result['text']}")
                    else:
                        self.set_result(f"You: {text}\n\nAssistant: {response}")

                    self.ids.waveform.set_speaking(True)
                    t2 = time.time()
                    speak(response)
                    print(f"[TIMING] speak: {time.time() - t2:.2f}s")
                    self.ids.waveform.set_speaking(False)
                else:
                    self.set_status("❌ Didn't catch that, try again")

            except Exception as e:
                print(f"[ERROR] Something went wrong in this exchange: {e}")
                self.set_status("⚠️ Error, retrying...")
                time.sleep(1)  # avoid tight error loop

        self.set_status("Ready")
        call_active = False
        Clock.schedule_once(lambda dt: self.reset_call_button())

    def reset_call_button(self):
        self.ids.call_btn.text = "Start Call"
        self.ids.call_btn.bg_color = (0.16, 0.55, 0.35, 1)
        self.ids.pause_btn.disabled = True


class VoiceAssistantApp(App):
    icon = 'Voice.ico'

    def build(self):
        self.title = "Voice Assistant"
        return AssistantLayout()

    def on_start(self):
        from kivy.core.window import Window
        Window.bind(on_request_close=self.on_request_close)

    def on_request_close(self, *args, **kwargs):
        self.minimize_to_tray()
        return True

    def minimize_to_tray(self):
        from kivy.core.window import Window
        Window.minimize()
        threading.Thread(target=self.setup_tray, daemon=True).start()

    def setup_tray(self):
        image = Image.open(resource_path("Voice.ico"))

        def on_show(icon, item):
            from kivy.core.window import Window
            Window.restore()
            icon.stop()

        def on_quit(icon, item):
            icon.stop()
            os._exit(0)

        menu = pystray.Menu(
            pystray.MenuItem("Show", on_show, default=True),
            pystray.MenuItem("Quit", on_quit)
        )

        tray_icon = pystray.Icon("VoiceAssistant", image, "Voice Assistant", menu)
        tray_icon.run()