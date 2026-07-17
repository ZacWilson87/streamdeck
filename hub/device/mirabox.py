"""Adapter for Mirabox Stream Dock N3-family (your 'henygen' MBOX N3 rebadge).

Uses Mirabox's official Python SDK:
    git clone https://github.com/MiraBoxSpace/StreamDock-SDKs
    (Python SDK lives under the python/ directory; see its README)

NOTE: Mirabox's SDK API surface has changed between releases and is only
partially documented, so this adapter is written against the common shape
(DeviceManager.enumerate() -> devices with .open(), .set_key_image(),
.set_key_callback(), .whell_* callbacks). If your SDK version differs,
this file is the ONLY place you need to touch — everything above the
device layer is SDK-agnostic. Alternative: the reverse-engineered
'mirajazz' library (Rust) documents the raw HID protocol if you ever
want zero vendor code.

Key size: N3 keys are 64x64 or 96x96 px depending on revision; we render
96x96 and downscale here if the SDK reports a smaller size.
"""
import threading

from . import BaseDevice


class MiraboxDevice(BaseDevice):
    def __init__(self):
        from StreamDock.DeviceManager import DeviceManager  # vendor SDK
        devices = DeviceManager().enumerate()
        if not devices:
            raise RuntimeError("no Mirabox device found")
        self.dev = devices[0]
        self.key_size = 96

    def start(self):
        self.dev.open()
        self.dev.set_key_callback(self._on_key)
        # Knobs/buttons arrive via the SDK's dial/whell callbacks on N3.
        for name in ("set_dial_callback", "set_whell_callback"):
            if hasattr(self.dev, name):
                getattr(self.dev, name)(self._on_dial)
        threading.Thread(target=getattr(self.dev, "listen", lambda: None),
                         daemon=True).start()

    def _on_key(self, _dev, index, pressed):
        # SDK indexes keys 1..6 on some firmwares; normalize to 0..5
        i = index - 1 if index >= 1 else index
        if 0 <= i <= 5:
            self._cb(("key", i, bool(pressed)))
        elif 6 <= i <= 8:  # some revisions report physical buttons as keys 7-9
            self._cb(("button", i - 6, bool(pressed)))

    def _on_dial(self, _dev, dial_index, event, value=None):
        # event conventions vary: 'rotate' with +/- value, or 'press'/'release'
        if event in ("rotate", "turn"):
            self._cb(("knob_rotate", dial_index, int(value or 0)))
        elif event in ("press", "down"):
            self._cb(("knob_press", dial_index, True))
        elif event in ("release", "up"):
            self._cb(("knob_press", dial_index, False))

    def set_key_image(self, index, pil_image):
        img = pil_image.resize((self.key_size, self.key_size))
        # Most SDK versions accept a file path or raw JPEG bytes:
        import io
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        if hasattr(self.dev, "set_key_image_data"):
            self.dev.set_key_image_data(index + 1, buf.getvalue())
        else:
            import tempfile, os
            f = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            f.write(buf.getvalue()); f.close()
            self.dev.set_key_image(index + 1, f.name)
            os.unlink(f.name)
