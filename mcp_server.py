"""MCP server: configure the StreamDock Hub by chatting with Claude.

Run standalone for testing:  python mcp_server.py
Claude Desktop config (claude_desktop_config.json):

  {
    "mcpServers": {
      "streamdock": {
        "command": "python",
        "args": ["/absolute/path/to/streamdock-hub/mcp_server.py"]
      }
    }
  }

Then in a chat: "Add a key to my Slack profile that starts a huddle" —
Claude edits the YAML, the hub hot-reloads, the device updates in ~1s.

Requires: pip install mcp
"""
import os
import yaml

from mcp.server.fastmcp import FastMCP

ROOT = os.path.dirname(os.path.abspath(__file__))
PROFILE_DIR = os.path.join(ROOT, "profiles")

mcp = FastMCP("streamdock")

SCHEMA_HELP = """Profile schema (YAML):
name: <id>            # required, lowercase
label: <Key label>
order: <int>          # HOME view sort
match: <window/process substring for auto-switch>   # or {mac: ..., win: ...}
launch: {mac: <open -a name>, win: <exe/command>}
voice_hotkey: {mac: <combo>, win: <combo>}           # app's own dictation hotkey
big_knob_rotate: <action>     # optional, runs on big-knob rotation in APP view
keys:                          # max 6 shown; keep 'Home' last by convention
  - {label: Dictate, action: voice_toggle}
  - {label: X, action: {mac: hotkey cmd+x, win: hotkey ctrl+x}}
Actions: hotkey <combo> | type <text> | shell <cmd> | launch <app>
         | voice_toggle | voice_app | view HOME
Combos: cmd/ctrl/alt/shift/enter/esc/space/tab + letters, joined with +.
"""


def _path(name):
    safe = "".join(c for c in name.lower() if c.isalnum() or c in "-_")
    return os.path.join(PROFILE_DIR, f"{safe}.yaml")


def _load(name):
    p = _path(name)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save(name, data):
    os.makedirs(PROFILE_DIR, exist_ok=True)
    with open(_path(name), "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


@mcp.tool()
def schema() -> str:
    """Return the profile schema and action reference. Read this before editing."""
    return SCHEMA_HELP


@mcp.tool()
def list_apps() -> str:
    """List all app profiles currently on the device's HOME view."""
    if not os.path.isdir(PROFILE_DIR):
        return "(no profiles)"
    out = []
    for f in sorted(os.listdir(PROFILE_DIR)):
        if f.endswith((".yaml", ".yml")):
            d = _load(os.path.splitext(f)[0]) or {}
            keys = ", ".join(k.get("label", "?") for k in d.get("keys", []))
            out.append(f"- {d.get('name', f)}: keys=[{keys}]")
    return "\n".join(out) or "(no profiles)"


@mcp.tool()
def get_profile(name: str) -> str:
    """Get the full YAML for one app profile."""
    d = _load(name)
    return yaml.safe_dump(d, sort_keys=False) if d else f"no profile '{name}'"


@mcp.tool()
def upsert_profile(name: str, profile_yaml: str) -> str:
    """Create or replace an app profile. profile_yaml must follow schema().
    The device hot-reloads within ~1 second of saving."""
    data = yaml.safe_load(profile_yaml)
    if not isinstance(data, dict):
        return "error: YAML must be a mapping"
    data["name"] = name.lower()
    if len(data.get("keys", [])) > 6:
        return "error: max 6 keys per view (6 LCD keys on the device)"
    _save(name, data)
    return f"saved '{name}' — device will update momentarily"


@mcp.tool()
def add_key(app: str, label: str, action_mac: str = "", action_win: str = "",
            position: int = -1) -> str:
    """Add one key to an existing app profile. Actions per schema(), e.g.
    'hotkey cmd+shift+h'. Leave action_win empty to reuse action_mac.
    position -1 inserts before the Home key."""
    d = _load(app)
    if d is None:
        return f"no profile '{app}' — use upsert_profile to create it"
    keys = d.setdefault("keys", [])
    if len(keys) >= 6:
        return "error: profile already has 6 keys; remove one first"
    action = (action_mac if (not action_win or action_win == action_mac)
              else {"mac": action_mac, "win": action_win})
    entry = {"label": label, "action": action}
    if position == -1 and keys and keys[-1].get("action") == "view HOME":
        keys.insert(len(keys) - 1, entry)
    elif 0 <= position < len(keys):
        keys.insert(position, entry)
    else:
        keys.append(entry)
    _save(app, d)
    return f"added key '{label}' to '{app}'"


@mcp.tool()
def remove_key(app: str, label: str) -> str:
    """Remove a key (by label) from an app profile."""
    d = _load(app)
    if d is None:
        return f"no profile '{app}'"
    before = len(d.get("keys", []))
    d["keys"] = [k for k in d.get("keys", []) if k.get("label") != label]
    _save(app, d)
    return ("removed" if len(d["keys"]) < before else
            f"no key labeled '{label}' in '{app}'")


@mcp.tool()
def remove_app(name: str) -> str:
    """Delete an app profile from the device entirely."""
    p = _path(name)
    if os.path.exists(p):
        os.remove(p)
        return f"removed '{name}'"
    return f"no profile '{name}'"


if __name__ == "__main__":
    mcp.run()
