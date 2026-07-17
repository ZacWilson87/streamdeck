"""StreamDock Hub — cross-platform app switcher + contextual controls
for Mirabox N3-family stream docks (6 LCD keys, 1 big knob, 2 small knobs, 3 buttons).

Views:
  HOME  : paginated list of app icons; big knob scrolls pages; tap = focus/launch app
  APP   : per-app contextual keys defined in profiles/*.yaml
Gestures:
  Big knob triple-press (or long-press) -> back to HOME
  Focus follows the OS: alt-tabbing to an app switches the deck to its APP view
"""
import time
import threading
import queue

from .config import load_profiles, load_settings
from .render import render_app_key, render_action_key, render_blank
from .actions import ActionRunner
from .device import get_device
from .platform_io import get_platform
from .voice import VoiceRecorder

TRIPLE_PRESS_WINDOW = 0.9   # seconds for 3 knob presses
LONG_PRESS_SECS = 0.8
KEYS = 6


class Hub:
    def __init__(self):
        self.settings = load_settings()
        self.profiles = load_profiles()          # ordered dict name -> profile
        self.platform = get_platform()
        self.device = get_device(self.settings)
        self.actions = ActionRunner(self.platform, self)
        self.voice = VoiceRecorder(self.settings, self.platform)

        self.view = "HOME"
        self.page = 0
        self.active_profile = None               # profile shown in APP view
        self._knob_presses = []                  # timestamps for triple-press
        self._events = queue.Queue()
        self._last_focus = None

    # ---------- rendering ----------
    def redraw(self):
        if self.view == "HOME":
            apps = list(self.profiles.values())
            start = self.page * KEYS
            for i in range(KEYS):
                idx = start + i
                if idx < len(apps):
                    p = apps[idx]
                    self.device.set_key_image(i, render_app_key(p))
                else:
                    self.device.set_key_image(i, render_blank())
        else:  # APP view
            keys = (self.active_profile or {}).get("keys", [])
            for i in range(KEYS):
                if i < len(keys):
                    img = render_action_key(keys[i], recording=self.voice.is_recording)
                    self.device.set_key_image(i, img)
                else:
                    self.device.set_key_image(i, render_blank())

    def go_home(self):
        self.view = "HOME"
        self.active_profile = None
        self.redraw()

    def go_app(self, profile):
        self.view = "APP"
        self.active_profile = profile
        self.redraw()

    # ---------- event handling ----------
    def on_key(self, index, pressed):
        if not pressed:
            return
        if self.view == "HOME":
            apps = list(self.profiles.values())
            idx = self.page * KEYS + index
            if idx < len(apps):
                p = apps[idx]
                self.platform.launch_or_focus(p)
                self.go_app(p)
        else:
            keys = (self.active_profile or {}).get("keys", [])
            if index < len(keys):
                self.actions.run(keys[index], self.active_profile)
                self.redraw()  # refresh (e.g. mic recording state)

    def on_big_knob_rotate(self, delta):
        if self.view == "HOME":
            pages = max(1, -(-len(self.profiles) // KEYS))
            self.page = (self.page + (1 if delta > 0 else -1)) % pages
            self.redraw()
        else:
            act = (self.active_profile or {}).get("big_knob_rotate")
            if act:
                self.actions.run({"action": act}, self.active_profile)

    def on_big_knob_press(self, pressed):
        now = time.time()
        if pressed:
            self._knob_down_at = now
            self._knob_presses = [t for t in self._knob_presses
                                  if now - t < TRIPLE_PRESS_WINDOW]
            self._knob_presses.append(now)
            if len(self._knob_presses) >= 3:
                self._knob_presses = []
                self.go_home()
        else:
            if now - getattr(self, "_knob_down_at", now) >= LONG_PRESS_SECS:
                self.go_home()  # long-press fallback gesture

    def on_focus_change(self, window_title, process_name):
        """Auto-switch deck view when the user changes app focus in the OS."""
        for p in self.profiles.values():
            m = p.get("match", "").lower()
            if m and (m in (window_title or "").lower()
                      or m in (process_name or "").lower()):
                if self.active_profile is not p:
                    self.go_app(p)
                return
        # focused app has no profile: stay where we are (don't yank the UI)

    # ---------- loops ----------
    def _focus_loop(self):
        while True:
            try:
                title, proc = self.platform.get_focused_window()
                key = (title, proc)
                if key != self._last_focus:
                    self._last_focus = key
                    self._events.put(("focus", title, proc))
            except Exception:
                pass
            self._check_profile_changes()
            time.sleep(0.5)

    def _check_profile_changes(self):
        """Hot-reload: if any profile file changed, reload and redraw."""
        from .config import PROFILE_DIR
        import os
        try:
            stamp = tuple(sorted(
                (f, os.path.getmtime(os.path.join(PROFILE_DIR, f)))
                for f in os.listdir(PROFILE_DIR)
                if f.endswith((".yaml", ".yml"))))
        except FileNotFoundError:
            return
        if stamp != getattr(self, "_profile_stamp", None):
            first = getattr(self, "_profile_stamp", None) is None
            self._profile_stamp = stamp
            if first:
                return
            active = self.active_profile["name"] if self.active_profile else None
            self.profiles = load_profiles()
            self.active_profile = self.profiles.get(active) if active else None
            if self.view == "APP" and self.active_profile is None:
                self.view = "HOME"
            self._events.put(("redraw",))

    def run(self):
        self.device.set_event_callback(lambda ev: self._events.put(ev))
        threading.Thread(target=self._focus_loop, daemon=True).start()
        self.device.start()
        self.redraw()
        print("StreamDock Hub running. Ctrl+C to quit.")
        while True:
            ev = self._events.get()
            kind = ev[0]
            if kind == "key":
                self.on_key(ev[1], ev[2])
            elif kind == "knob_rotate" and ev[1] == 0:
                self.on_big_knob_rotate(ev[2])
            elif kind == "knob_press" and ev[1] == 0:
                self.on_big_knob_press(ev[2])
            elif kind == "knob_rotate":
                act = (self.active_profile or {}).get(f"knob{ev[1]}_rotate")
                if act:
                    self.actions.run({"action": act}, self.active_profile)
            elif kind == "button":
                # 3 physical buttons: 0=push-to-talk toggle, 1=approve/enter, 2=escape
                if ev[2]:
                    if ev[1] == 0:
                        self.actions.run({"action": "voice_toggle"}, self.active_profile)
                        self.redraw()
                    elif ev[1] == 1:
                        self.platform.send_hotkey("enter")
                    elif ev[1] == 2:
                        self.platform.send_hotkey("escape")
            elif kind == "focus":
                self.on_focus_change(ev[1], ev[2])
            elif kind == "redraw":
                self.redraw()


def main():
    Hub().run()


if __name__ == "__main__":
    main()
