"""Adapter for Mirabox Stream Dock N3-family (the 'henygen' MBOX N3 rebadge).

Uses Mirabox's official Python SDK (package name ``streamdock``):
    git clone https://github.com/MiraboxSpace/StreamDock-Device-SDK
    pip install -e StreamDock-Device-SDK/Python-SDK
The SDK ships its own native transport (libtransport_*.dylib/.so/.dll), so no
system hidapi install is needed. It must be installed *editable* on macOS so
the bundled dylib next to the Python sources stays reachable.

This file is the ONLY place that touches the vendor SDK; everything above the
device layer is SDK-agnostic. It is written against the current SDK shape:

  DeviceManager().enumerate() -> [StreamDock...]      # device objects
  dev.open(); dev.init()                              # open + read thread starts
  dev.set_key_callback(cb)  where cb(device, InputEvent)
  dev.set_key_image(logical_key 1..N, path)           # path to an image file
  dev.refresh()                                       # flush framebuffer to screen
  dev.close()

The N3 exposes 18 logical inputs: 6 LCD keys (KEY_1..KEY_6), 3 physical buttons
(KEY_7..KEY_9), and 3 knobs (KNOB_1 bottom-left, KNOB_2 bottom-right, KNOB_3
top) that each rotate (LEFT/RIGHT) and press. See StreamDockN3.decode_input_event.
"""
import os
import tempfile
import threading

from . import BaseDevice


class MiraboxDevice(BaseDevice):
    def __init__(self):
        from StreamDock.DeviceManager import DeviceManager  # vendor SDK
        devices = DeviceManager().enumerate()
        if not devices:
            raise RuntimeError("no Mirabox device found")
        self.dev = devices[0]
        self._refresh_timer = None
        self._refresh_lock = threading.Lock()
        self._tmpdir = tempfile.mkdtemp(prefix="streamdock-keys-")

        # SDK logical-key -> hub event mapping.
        from StreamDock.InputTypes import ButtonKey, KnobId, Direction
        self._ButtonKey = ButtonKey
        self._Direction = Direction
        # LCD keys KEY_1..KEY_6 -> hub key index 0..5
        self._lcd_keys = {getattr(ButtonKey, f"KEY_{i + 1}"): i for i in range(6)}
        # Physical buttons KEY_7..KEY_9 -> hub button index 0..2
        self._buttons = {getattr(ButtonKey, f"KEY_{i + 7}"): i for i in range(3)}
        # Knobs -> hub knob index. Confirmed on the N3 via tools/knob_probe.py:
        #   KNOB_3 = big knob        -> index 0 (HOME gesture / paging, big_knob_*)
        #   KNOB_1 = left small knob -> index 1 (knob1)
        #   KNOB_2 = right small knob-> index 2 (knob2)
        self._knobs = {KnobId.KNOB_3: 0, KnobId.KNOB_1: 1, KnobId.KNOB_2: 2}

    def start(self):
        self.dev.open()
        self.dev.init()            # wake screen, full brightness, clear icons
        self.dev.set_key_callback(self._on_event)

    # ---------- input ----------
    def _on_event(self, _device, event):
        from StreamDock.InputTypes import EventType
        et = event.event_type
        if et == EventType.BUTTON:
            if event.key in self._lcd_keys:
                self._cb(("key", self._lcd_keys[event.key], event.state == 1))
            elif event.key in self._buttons:
                self._cb(("button", self._buttons[event.key], event.state == 1))
        elif et == EventType.KNOB_ROTATE:
            idx = self._knobs.get(event.knob_id)
            if idx is not None:
                delta = 1 if event.direction == self._Direction.RIGHT else -1
                self._cb(("knob_rotate", idx, delta))
        elif et == EventType.KNOB_PRESS:
            idx = self._knobs.get(event.knob_id)
            if idx is not None:
                self._cb(("knob_press", idx, event.state == 1))

    # ---------- output ----------
    def set_key_image(self, index, pil_image):
        # SDK takes a file path and a logical key number (1-based); it handles
        # rotation/resize/format for the N3 internally.
        path = os.path.join(self._tmpdir, f"key{index}.png")
        pil_image.save(path)
        self.dev.set_key_image(index + 1, path)
        self._schedule_refresh()

    def _schedule_refresh(self):
        # Coalesce the per-key writes of one redraw into a single screen flush.
        with self._refresh_lock:
            if self._refresh_timer is not None:
                self._refresh_timer.cancel()
            self._refresh_timer = threading.Timer(0.05, self._do_refresh)
            self._refresh_timer.daemon = True
            self._refresh_timer.start()

    def _do_refresh(self):
        try:
            self.dev.refresh()
        except Exception as e:
            print(f"device: refresh failed: {e}")

    def close(self):
        try:
            self.dev.set_key_callback(None)
            self.dev.close()
        except Exception:
            pass
