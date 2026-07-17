"""Executes actions declared in profile key definitions.

Supported action strings:
  hotkey <combo>     e.g. "hotkey ctrl+alt+cmd+m"
  type <text>        types literal text into the focused field
  launch <target>    launch/focus an app (target = profile launch string)
  shell <command>    run a shell command
  voice_toggle       start/stop universal push-to-talk dictation
  voice_claude       alias: sends the app's own voice hotkey if defined, else voice_toggle
  view HOME          return deck to app list
"""
import subprocess
import shlex


class ActionRunner:
    def __init__(self, platform, hub):
        self.platform = platform
        self.hub = hub

    def run(self, keydef, profile):
        action = (keydef.get("action") or "").strip()
        if not action:
            return
        if action == "voice_toggle":
            self.hub.voice.toggle()
            return
        if action == "voice_app":
            combo = (profile or {}).get("voice_hotkey")
            if combo:
                self.platform.send_hotkey(combo)
            else:
                self.hub.voice.toggle()
            return
        verb, _, rest = action.partition(" ")
        if verb == "hotkey":
            self.platform.send_hotkey(rest)
        elif verb == "type":
            self.platform.type_text(rest)
        elif verb == "launch":
            self.platform.launch_or_focus({"launch": rest, "match": rest})
        elif verb == "shell":
            subprocess.Popen(shlex.split(rest))
        elif verb == "view" and rest.upper() == "HOME":
            self.hub.go_home()
