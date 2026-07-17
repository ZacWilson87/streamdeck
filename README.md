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
- **Voice** — two independent paths:
  - *App-native* (`voice_app`): the deck sends the app's own dictation shortcut
    (`voice_hotkey` in the profile) so the app's speech model handles it. Claude
    Desktop on macOS is **Cmd+D**. Higher quality, no local transcription.
  - *Universal* (`voice_toggle`, and physical button 1): the hub itself records,
    transcribes (local faster-whisper or OpenAI Whisper), and types the text into
    whatever field is focused — for apps with no native voice (e.g. a browser).

## Install
1. Python 3.10+, then: `pip install -r requirements.txt`
   (or `uv sync` — the device SDK below is already wired in as a path source).
2. Device SDK: clone the vendor SDK **next to this repo** and install it
   *editable* (the SDK ships its own native transport library beside its Python
   sources, so a non-editable install on macOS loses the dylib):
   ```
   git clone https://github.com/MiraboxSpace/StreamDock-Device-SDK
   uv sync   # picks up ../StreamDock-Device-SDK/Python-SDK via [tool.uv.sources]
   ```
   Plain pip instead of uv: `pip install -e ../StreamDock-Device-SDK/Python-SDK`.
   The SDK's Python package is named `StreamDock` (import path) / `streamdock`
   (distribution). No system `hidapi` needed — it's bundled in the transport lib.
   Note: the separate `StreamDock-Plugin-SDK` repo is for plugins to Mirabox's
   own desktop app — not what we want. If your SDK version's API differs, adjust
   only `hub/device/mirabox.py` — see its notes. (Alternative protocol reference:
   the open-source `mirajazz` project.)
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

### Icons
Icons live in `icons/` and are committed, so they sync to both machines:
- **App icons (HOME view):** `icons/app-<name>.png` is picked up automatically
  for the profile whose `name:` matches (e.g. `app-slack.png`). On macOS you can
  pull an app's real icon with `sips`:
  `sips -s format png -z 256 256 "/Applications/Slack.app/Contents/Resources/electron.icns" --out icons/app-slack.png`
- **Action icons (APP view):** white symbol glyphs at `icons/sym-*.png`. Point a
  key at one with `icon: sym-search.png`. `voice_toggle`, `voice_app`, and
  `view HOME` auto-pick a glyph, so they need no `icon:` field. Regenerate/extend
  the glyph set from Lucide with `tools/gen_symbol_icons.py`.
- Any `icon:` value is just a filename in `icons/`; missing icons fall back to a
  colored initial tile (apps) or a text label (actions).

## Both machines
Copy this folder (or sync it via git/cloud) to the Mac and the PC. Profiles are
shared; per-OS fields resolve automatically on each machine. The device just
moves with you over USB.
