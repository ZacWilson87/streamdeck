"""Platform layer: the only OS-specific code in the project.

Interface:
  get_focused_window() -> (window_title, process_name)
  launch_or_focus(profile)
  send_hotkey("ctrl+alt+cmd+m")
  type_text("hello")
"""
import platform as _plat
import subprocess
import shlex


def get_platform():
    if _plat.system() == "Darwin":
        return MacPlatform()
    if _plat.system() == "Windows":
        return WindowsPlatform()
    raise RuntimeError("Stage 1 supports macOS and Windows")


class _PynputMixin:
    """Hotkeys + typing via pynput (works on both OSes)."""
    _KEYMAP = {
        "cmd": "cmd", "win": "cmd", "ctrl": "ctrl", "alt": "alt",
        "option": "alt", "opt": "alt", "shift": "shift", "enter": "enter",
        "return": "enter", "escape": "esc", "esc": "esc", "space": "space",
        "tab": "tab", "caps_lock": "caps_lock", "capslock": "caps_lock",
    }

    def _kb(self):
        from pynput.keyboard import Controller
        if not hasattr(self, "_kb_ctl"):
            self._kb_ctl = Controller()
        return self._kb_ctl

    def send_hotkey(self, combo):
        from pynput.keyboard import Key
        kb = self._kb()
        parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
        keys = []
        for p in parts:
            name = self._KEYMAP.get(p, p)
            keys.append(getattr(Key, name) if hasattr(Key, name) else p)
        for k in keys:
            kb.press(k)
        for k in reversed(keys):
            kb.release(k)

    def type_text(self, text):
        self._kb().type(text)


class MacPlatform(_PynputMixin):
    def get_focused_window(self):
        script = ('tell application "System Events" to get name of first '
                  'application process whose frontmost is true')
        proc = subprocess.run(["osascript", "-e", script],
                              capture_output=True, text=True).stdout.strip()
        return proc, proc

    def launch_or_focus(self, profile):
        target = profile.get("launch") or profile.get("match") or profile.get("name")
        subprocess.Popen(["open", "-a", target])


class WindowsPlatform(_PynputMixin):
    def get_focused_window(self):
        import ctypes
        import ctypes.wintypes as wt
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        pid = wt.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc = self._proc_name(pid.value)
        return buf.value, proc

    @staticmethod
    def _proc_name(pid):
        try:
            import psutil
            return psutil.Process(pid).name()
        except Exception:
            return ""

    def launch_or_focus(self, profile):
        target = profile.get("launch") or profile.get("name")
        # 'start' resolves app aliases, .exe paths, and URIs alike
        subprocess.Popen(f'start "" {shlex.quote(target)}', shell=True)
