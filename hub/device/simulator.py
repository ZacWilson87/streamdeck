"""Terminal simulator: develop and test the hub with no hardware attached.

Controls (type + Enter):
  1..6      tap LCD key 1-6
  <  >      rotate big knob left/right
  p         press big knob once (type 'p' 3x quickly for triple-press... or 'ppp')
  ppp       triple-press big knob (back to HOME)
  b1 b2 b3  physical buttons (b1 = push-to-talk)
  k1< k1>   small knob 1 rotate, k2< k2> small knob 2
  q         quit
Key images are saved to /tmp/deck-key-{i}.png so you can see the rendered UI.
"""
import sys
import threading
import time

from . import BaseDevice


class SimulatorDevice(BaseDevice):
    def start(self):
        threading.Thread(target=self._repl, daemon=True).start()

    def set_key_image(self, index, pil_image):
        try:
            pil_image.save(f"/tmp/deck-key-{index}.png")
        except Exception:
            pass

    def _repl(self):
        print(__doc__)
        for line in sys.stdin:
            cmd = line.strip().lower()
            if cmd == "q":
                raise SystemExit
            elif cmd in "123456" and cmd:
                i = int(cmd) - 1
                self._cb(("key", i, True)); self._cb(("key", i, False))
            elif cmd == "<":
                self._cb(("knob_rotate", 0, -1))
            elif cmd == ">":
                self._cb(("knob_rotate", 0, 1))
            elif cmd == "p":
                self._cb(("knob_press", 0, True)); self._cb(("knob_press", 0, False))
            elif cmd == "ppp":
                for _ in range(3):
                    self._cb(("knob_press", 0, True))
                    self._cb(("knob_press", 0, False))
                    time.sleep(0.05)
            elif cmd in ("b1", "b2", "b3"):
                i = int(cmd[1]) - 1
                self._cb(("button", i, True)); self._cb(("button", i, False))
            elif cmd in ("k1<", "k1>", "k2<", "k2>"):
                self._cb(("knob_rotate", int(cmd[1]), 1 if cmd[2] == ">" else -1))
