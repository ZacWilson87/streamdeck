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
import signal
import threading
import queue

from .config import load_profiles, load_settings
from .render import render_app_key, render_action_key, render_blank
from .actions import ActionRunner
from .device import get_device
from .platform_io import get_platform
from .voice import VoiceRecorder

TRIPLE_PRESS_WINDOW = 0.6   # seconds for 3 knob presses (also the single-tap Select delay)
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
        self._knob_taps = []                     # release timestamps for tap/triple-press
        self._select_timer = None                # fires a lone tap as "select"
        self._held_combo = None                  # chord currently held by a "hold" key
        self._hold_watchdog = None               # safety auto-release for a stuck hold
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
        if self.view == "HOME":
            if not pressed:
                return
            apps = list(self.profiles.values())
            idx = self.page * KEYS + index
            if idx < len(apps):
                p = apps[idx]
                self.platform.launch_or_focus(p)
                self.go_app(p)
            return
        # APP view
        keys = (self.active_profile or {}).get("keys", [])
        if index >= len(keys):
            return
        action = keys[index].get("action") or ""
        # "hold <combo>": push-to-talk / momentary — hold the chord while the key
        # is held, release it when the key is released (e.g. Codex dictation ⌃⇧D).
        if isinstance(action, str) and action.startswith("hold "):
            self._handle_hold(action[5:].strip(), pressed)
            return
        if not pressed:
            return
        self.actions.run(keys[index], self.active_profile)
        self.redraw()  # refresh (e.g. mic recording state)

    def _handle_hold(self, combo, pressed):
        if pressed:
            if self._held_combo:                 # never stack holds
                self.platform.hotkey_up(self._held_combo)
            self.platform.hotkey_down(combo)
            self._held_combo = combo
            self._arm_hold_watchdog()
        else:
            self._release_hold()

    def _arm_hold_watchdog(self):
        # Safety net: if a key-release is ever missed, don't leave modifiers stuck.
        self._cancel_hold_watchdog()
        self._hold_watchdog = threading.Timer(30.0, self._release_hold)
        self._hold_watchdog.daemon = True
        self._hold_watchdog.start()

    def _cancel_hold_watchdog(self):
        if self._hold_watchdog is not None:
            self._hold_watchdog.cancel()
            self._hold_watchdog = None

    def _release_hold(self):
        self._cancel_hold_watchdog()
        if self._held_combo:
            self.platform.hotkey_up(self._held_combo)
            self._held_combo = None

    # config key for each hub knob index (see hub/device/mirabox.py)
    KNOB_KEYS = {0: "big_knob", 1: "knob1", 2: "knob2"}

    def _run_knob(self, index, slot):
        """Run the profile's knob binding for a slot ('left'|'right'|'press').

        Binding shape in a profile:
            knob1:
              left:  <action>
              right: <action>
              press: <action>
        """
        cfg = (self.active_profile or {}).get(self.KNOB_KEYS.get(index, ""))
        act = cfg.get(slot) if isinstance(cfg, dict) else None
        if act:
            self.actions.run({"action": act}, self.active_profile)

    def on_big_knob_rotate(self, delta):
        if self.view == "HOME":
            pages = max(1, -(-len(self.profiles) // KEYS))
            self.page = (self.page + (1 if delta > 0 else -1)) % pages
            self.redraw()
        else:
            self._run_knob(0, "right" if delta > 0 else "left")

    def on_big_knob_press(self, pressed):
        """Big-knob gestures, resolved on release:
          long-press           -> HOME
          triple quick-tap     -> HOME
          single quick-tap     -> Select (fires after the multi-tap window so a
                                  lone tap can't be mistaken for the first of a
                                  triple-press; ~TRIPLE_PRESS_WINDOW of latency).
        """
        now = time.time()
        if pressed:
            self._knob_down_at = now
            return
        self._cancel_select_timer()
        if now - getattr(self, "_knob_down_at", now) >= LONG_PRESS_SECS:
            self._knob_taps = []
            self.go_home()
            return
        self._knob_taps = [t for t in self._knob_taps
                           if now - t < TRIPLE_PRESS_WINDOW]
        self._knob_taps.append(now)
        if len(self._knob_taps) >= 3:
            self._knob_taps = []
            self.go_home()
            return
        # maybe a lone tap: wait out the window, then treat as Select
        self._select_timer = threading.Timer(TRIPLE_PRESS_WINDOW, self._knob_select)
        self._select_timer.daemon = True
        self._select_timer.start()

    def _cancel_select_timer(self):
        if self._select_timer is not None:
            self._select_timer.cancel()
            self._select_timer = None

    def _knob_select(self):
        """Lone big-knob tap = Select. Enter by default; a profile can override
        with big_knob.press. Only in APP view, so it never fires stray keystrokes
        from HOME."""
        taps, self._knob_taps = self._knob_taps, []
        if len(taps) != 1 or self.view == "HOME":
            return
        cfg = (self.active_profile or {}).get("big_knob")
        act = cfg.get("press") if isinstance(cfg, dict) else None
        if act:
            self.actions.run({"action": act}, self.active_profile)
        else:
            self.platform.send_hotkey("enter")

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

    def shutdown(self):
        """Leave the device in a clean state: stop the mic and clear the deck.

        Without this, killing/Ctrl+C'ing the hub leaves the deck frozen on its
        last frame (e.g. a stale 'recording' key) because the screen keeps the
        last framebuffer until something tells it otherwise."""
        try:
            self._release_hold()          # never exit with a chord still held down
        except Exception:
            pass
        try:
            if getattr(self.voice, "is_recording", False):
                self.voice.stop()
        except Exception:
            pass
        close = getattr(self.device, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass

    def run(self):
        self.device.set_event_callback(lambda ev: self._events.put(ev))
        threading.Thread(target=self._focus_loop, daemon=True).start()
        self.device.start()
        self.redraw()
        # Turn a plain `kill`/SIGTERM into the same graceful path as Ctrl+C so the
        # deck always gets cleared on exit, not just on an interactive Ctrl+C.
        def _on_sigterm(*_):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, _on_sigterm)
        print("StreamDock Hub running. Ctrl+C to quit.")
        try:
            self._loop()
        except KeyboardInterrupt:
            print("\nStreamDock Hub shutting down.")
        finally:
            self.shutdown()

    def _loop(self):
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
                self._run_knob(ev[1], "right" if ev[2] > 0 else "left")
            elif kind == "knob_press":
                if ev[2]:  # press (small knobs 1..2; big knob handled above)
                    self._run_knob(ev[1], "press")
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
