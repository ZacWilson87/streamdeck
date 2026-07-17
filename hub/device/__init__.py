"""Device layer. Events pushed to the callback as tuples:
  ("key", index 0-5, pressed bool)
  ("knob_rotate", knob_index, delta)     # 0 = big knob, 1..2 = small knobs
  ("knob_press", knob_index, pressed)
  ("button", index 0-2, pressed)
"""


def get_device(settings):
    kind = (settings.get("device", {}) or {}).get("kind", "auto")
    if kind in ("auto", "mirabox"):
        try:
            from .mirabox import MiraboxDevice
            return MiraboxDevice()
        except Exception as e:
            if kind == "mirabox":
                raise
            print(f"device: Mirabox not available ({e}); using terminal simulator")
    from .simulator import SimulatorDevice
    return SimulatorDevice()


class BaseDevice:
    def set_event_callback(self, cb):
        self._cb = cb

    def start(self):
        raise NotImplementedError

    def set_key_image(self, index, pil_image):
        raise NotImplementedError
