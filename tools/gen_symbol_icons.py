"""Generate white symbol-icon PNGs for action keys from Lucide SVGs.

Lucide (https://lucide.dev) is ISC-licensed, so the rendered PNGs can live in
this repo and sync to every machine. This is a *build-time* tool — the hub only
ever loads the baked PNGs, so cairosvg/cairo are not runtime dependencies.

Run (once, on any machine with cairo available):
    uv pip install cairosvg
    DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib uv run python tools/gen_symbol_icons.py

App icons (app-*.png) are extracted separately from installed .app bundles, e.g.
    sips -s format png -z 256 256 "/Applications/Cursor.app/Contents/Resources/Cursor.icns" --out icons/app-cursor.png
"""
import os
import urllib.request

import cairosvg

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")
SIZE = 240
STROKE = "#ECECEC"          # near-white; render.py tints per state if needed
CDN = "https://unpkg.com/lucide-static@latest/icons/{}.svg"

# Lucide icon name -> our sym-<key>.png basename.
ICONS = {
    "mic": "mic",                 # push-to-talk dictation
    "audio-lines": "voice-app",   # app-native voice (Claude Quick Entry)
    "house": "home",              # back to HOME view
    "plus": "new-tab",            # new tab
    "undo-2": "reopen-tab",       # reopen closed tab
    "square-pen": "new-chat",     # new chat / compose
    "search": "search",           # search
    "inbox": "unreads",           # unread messages
    "sparkles": "ai-pane",        # AI panel
    "check": "accept",            # accept / confirm
    "x": "reject",                # reject / cancel
    "corner-down-left": "select", # Enter / open highlighted item
}


def render(lucide_name, out_name):
    svg = urllib.request.urlopen(CDN.format(lucide_name), timeout=30).read().decode()
    svg = svg.replace("currentColor", STROKE)
    out = os.path.join(ICON_DIR, f"sym-{out_name}.png")
    cairosvg.svg2png(bytestring=svg.encode(), write_to=out,
                     output_width=SIZE, output_height=SIZE)
    print(f"sym-{out_name}.png  <- lucide:{lucide_name}")


def main():
    os.makedirs(ICON_DIR, exist_ok=True)
    for lucide_name, out_name in ICONS.items():
        render(lucide_name, out_name)
    print(f"\nWrote {len(ICONS)} symbol icons to {ICON_DIR}")


if __name__ == "__main__":
    main()
