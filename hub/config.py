"""Loads profiles/*.yaml and settings.yaml."""
import os
import platform as _plat
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE_DIR = os.path.join(ROOT, "profiles")
SETTINGS_FILE = os.path.join(ROOT, "settings.yaml")
OS_KEY = "mac" if _plat.system() == "Darwin" else "win"


def _resolve_os(value):
    """A profile field may be a plain value or {win: ..., mac: ...}."""
    if isinstance(value, dict) and ("win" in value or "mac" in value):
        return value.get(OS_KEY)
    return value


def load_profiles():
    profiles = {}
    if not os.path.isdir(PROFILE_DIR):
        return profiles
    for fname in sorted(os.listdir(PROFILE_DIR)):
        if not fname.endswith((".yaml", ".yml")):
            continue
        with open(os.path.join(PROFILE_DIR, fname), "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        data.setdefault("name", os.path.splitext(fname)[0])
        # resolve per-OS fields at load time
        for field in ("launch", "match", "voice_hotkey"):
            if field in data:
                data[field] = _resolve_os(data[field])
        for key in data.get("keys", []):
            if "action" in key:
                key["action"] = _resolve_os(key["action"])
        # knob bindings: {left|right|press: <action>}, each possibly per-OS
        for knob in ("big_knob", "knob1", "knob2"):
            cfg = data.get(knob)
            if isinstance(cfg, dict):
                for slot in ("left", "right", "press"):
                    if slot in cfg:
                        cfg[slot] = _resolve_os(cfg[slot])
        data["order"] = data.get("order", 100)
        profiles[data["name"]] = data
    # stable ordering by 'order' then name
    return dict(sorted(profiles.items(), key=lambda kv: (kv[1]["order"], kv[0])))


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}
