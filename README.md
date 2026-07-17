# StreamDock Hub

Cross-platform (macOS + Windows) app switcher and contextual control surface
for Mirabox N3-family stream docks (incl. "henygen" MBOX N3 rebadges):
6 LCD keys, big knob + 2 small knobs, 3 physical buttons.

## What it does (stage 1)
- **HOME view** — LCD keys show your apps; tap to focus/launch. Big knob pages
  through more than 6 apps.
- **APP view** — per-app keys from `profiles/*.yaml`. The deck follows OS focus
  automatically (alt-tab to Cursor -> Cursor layout appears).
- **Back to HOME** — triple-press the big knob (long-press also works).
- **Voice** — physical button 1 (or a "Dictate" key) toggles universal
  push-to-talk: records, transcribes (local faster-whisper or OpenAI Whisper),
  and types the text into whatever input field is focused — any app.
  For Claude Desktop on macOS, the `Voice (app)` key sends Claude's own
  dictation shortcut (rebind it in Claude Settings > General from Caps Lock to
  Ctrl+Opt+Cmd+M, since synthetic Caps Lock is unreliable). Note Claude's
  shortcut opens Quick Entry (a new-chat popup); use "Dictate here" to speak
  into the chat you currently have open.

## Install
1. Python 3.10+, then: `pip install -r requirements.txt`
2. Device SDK: clone https://github.com/MiraboxSpace/StreamDock-Device-SDK and
   install its Python package (`pip install -e StreamDock-Device-SDK/Python-SDK`,
   or `uv pip install -e ...`). On macOS also `brew install hidapi`. Note: the
   separate StreamDock-Plugin-SDK repo is for plugins to Mirabox's own desktop
   app — not what we want. If your SDK version's API differs, adjust only
   `hub/device/mirabox.py` — see its notes.
   (Alternative protocol reference: the open-source `mirajazz` project.)
3. macOS permissions: System Settings > Privacy & Security ->
   Accessibility (for typing/hotkeys) and Microphone for your terminal/Python.
4. Run: `python run.py`

No device handy? It falls back to a terminal simulator; rendered key images
are written to /tmp/deck-key-*.png so you can see the UI.

## Configure by chatting with Claude

**Claude Desktop (MCP):** add to claude_desktop_config.json:
```json
{"mcpServers": {"streamdock": {"command": "python",
  "args": ["/absolute/path/to/streamdock-hub/mcp_server.py"]}}}
```
Then just say things like "add a huddle key to my Slack profile" or "put
Figma on my deck with zoom shortcuts" — Claude edits the profile and the
running hub hot-reloads the device within ~1 second. (`pip install mcp`.)

**Claude Code:** the repo ships a skill at .claude/skills/streamdock/ — open
the repo in Claude Code and ask for changes in plain language.

## Add an app

Fastest way: run `python add_app.py` — a 30-second wizard that asks for the
app name, window match, launch commands, and any hotkeys, then writes the
profile for you.

Or by hand:
Drop a YAML in `profiles/` (see existing ones). Per-OS values:
```yaml
launch: {mac: "Obsidian", win: "obsidian.exe"}
keys:
  - {label: Search, action: {mac: hotkey cmd+o, win: hotkey ctrl+o}}
```
Actions: `hotkey <combo>`, `type <text>`, `shell <cmd>`, `launch <app>`,
`voice_toggle`, `voice_app`, `view HOME`.
Optional 96x96 PNG icons in `icons/` (named in the profile as `icon: name.png`);
otherwise a colored initial tile is generated.

## Both machines
Copy this folder (or sync it via git/cloud) to the Mac and the PC. Profiles are
shared; per-OS fields resolve automatically on each machine. The device just
moves with you over USB.
