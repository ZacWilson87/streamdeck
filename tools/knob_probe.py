"""Diagnostic: print which SDK knob / hub-index fires when you turn or press a
knob, so we can confirm the physical<->logical mapping instead of guessing.

Run it, then turn/press each knob when prompted:
    uv run python tools/knob_probe.py
Ctrl+C to stop.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from StreamDock.DeviceManager import DeviceManager
from StreamDock.InputTypes import EventType

# Same physical->hub-index mapping the hub currently assumes (hub/device/mirabox.py).
from StreamDock.InputTypes import KnobId
HUB_INDEX = {KnobId.KNOB_3: 0, KnobId.KNOB_1: 1, KnobId.KNOB_2: 2}
NAME = {0: "big_knob (index 0)", 1: "knob1 (index 1)", 2: "knob2 (index 2)"}


def on_event(_dev, ev):
    if ev.event_type == EventType.KNOB_ROTATE:
        idx = HUB_INDEX.get(ev.knob_id)
        print(f"ROTATE  sdk={ev.knob_id.value:8} dir={ev.direction.value:5} "
              f"-> hub {NAME.get(idx, '?')}", flush=True)
    elif ev.event_type == EventType.KNOB_PRESS:
        idx = HUB_INDEX.get(ev.knob_id)
        state = "press" if ev.state == 1 else "release"
        print(f"PRESS   sdk={ev.knob_id.value:8} {state:7} "
              f"-> hub {NAME.get(idx, '?')}", flush=True)


def main():
    docks = DeviceManager().enumerate()
    if not docks:
        print("no device found")
        return
    dev = docks[0]
    dev.open()
    dev.init()
    dev.set_key_callback(on_event)
    print("Ready. Turn the BIG knob, then each small knob (and press each). Ctrl+C to stop.",
          flush=True)
    try:
        import time
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        dev.set_key_callback(None)
        dev.close()


if __name__ == "__main__":
    main()
