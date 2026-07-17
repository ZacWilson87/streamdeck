"""Renders 96x96 (configurable) key images with Pillow.

Icons live in ``icons/``:
  app-<name>.png   full-colour application icons (HOME view) — fill the key
  sym-<name>.png   white symbol glyphs (APP view actions) — centred on a tile

App keys fall back to a coloured initial tile, and action keys to a text label,
so the deck still works before icons exist. See tools/gen_symbol_icons.py for
how the sym-*.png glyphs are produced (Lucide, ISC-licensed).
"""
import os
import hashlib
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_DIR = os.path.join(ROOT, "icons")
KEY_SIZE = 96  # Mirabox N3 keys accept ~96x96; adapter rescales if needed

TILE_BG = (24, 24, 28)
BLANK_BG = (12, 12, 14)
REC_BG = (150, 28, 28)
GLYPH = (236, 236, 236)
CAPTION = (232, 232, 232)

# Action -> symbol glyph, so keys get an icon without one being spelled out in
# every profile. An explicit `icon:` in the profile always wins over this.
_ACTION_SYM = {
    "voice_toggle": "sym-mic.png",
    "voice_app": "sym-voice-app.png",
    "view HOME": "sym-home.png",
}

_font_cache = {}
_icon_cache = {}


def _font(size):
    if size not in _font_cache:
        for path in (
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",   # macOS
            "/System/Library/Fonts/SFNSDisplay.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
            "C:/Windows/Fonts/segoeuib.ttf",                        # Windows
        ):
            try:
                _font_cache[size] = ImageFont.truetype(path, size)
                break
            except Exception:
                continue
        else:
            _font_cache[size] = ImageFont.load_default()
    return _font_cache[size]


def _color_for(name):
    h = hashlib.md5(name.encode()).digest()
    return (80 + h[0] % 150, 80 + h[1] % 150, 80 + h[2] % 150)


def _base(bg=TILE_BG):
    return Image.new("RGB", (KEY_SIZE, KEY_SIZE), bg)


def _load_rgba(icon_name):
    if not icon_name:
        return None
    if icon_name not in _icon_cache:
        path = os.path.join(ICON_DIR, icon_name)
        _icon_cache[icon_name] = (
            Image.open(path).convert("RGBA") if os.path.exists(path) else None
        )
    return _icon_cache[icon_name]


def _fit(img, box):
    w, h = img.size
    scale = min(box / w, box / h)
    return img.resize((max(1, round(w * scale)), max(1, round(h * scale))),
                      Image.LANCZOS)


def _paste_center(tile, img, dy=0):
    x = (KEY_SIZE - img.width) // 2
    y = (KEY_SIZE - img.height) // 2 + dy
    tile.paste(img, (x, y), img)


def _tint(glyph, rgb):
    """Recolour a white glyph, keeping its alpha."""
    solid = Image.new("RGBA", glyph.size, rgb + (255,))
    solid.putalpha(glyph.split()[3])
    return solid


def _caption(img, text, y, size=12, fill=CAPTION):
    if not text:
        return
    d = ImageDraw.Draw(img)
    f = _font(size)
    box = d.textbbox((0, 0), text, font=f)
    d.text(((KEY_SIZE - (box[2] - box[0])) / 2, y), text, font=f, fill=fill)


def _center_text(img, text, size, fill=(240, 240, 240), dy=0):
    d = ImageDraw.Draw(img)
    f = _font(size)
    box = d.textbbox((0, 0), text, font=f)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((KEY_SIZE - w) / 2, (KEY_SIZE - h) / 2 + dy - box[1]), text,
           font=f, fill=fill)


def render_app_key(profile):
    """HOME view: full-colour app icon filling the key (no text)."""
    icon = _load_rgba(profile.get("icon") or f"app-{profile['name']}.png")
    tile = _base()
    if icon is not None:
        _paste_center(tile, _fit(icon, 92))
        return tile
    # fallback: coloured initial tile
    tile = _base(_color_for(profile["name"]))
    _center_text(tile, (profile.get("label") or profile["name"])[0].upper(), 46)
    return tile


def render_action_key(keydef, recording=False):
    label = keydef.get("label", "")
    action = keydef.get("action")
    is_voice = action == "voice_toggle"

    glyph_name = keydef.get("icon") or _ACTION_SYM.get(
        action if isinstance(action, str) else "")
    glyph = _load_rgba(glyph_name)

    tile = _base(REC_BG if (is_voice and recording) else TILE_BG)
    if glyph is not None:
        g = _fit(glyph, 46)
        if is_voice and recording:
            g = _tint(g, (255, 235, 235))
        _paste_center(tile, g, dy=-12)
        _caption(tile, "recording" if (is_voice and recording) else label[:12], 68)
        return tile

    # no glyph: centred text label (keeps unknown/custom keys working)
    _center_text(tile, label[:10] or "?", 15)
    return tile


def render_blank():
    return _base(BLANK_BG)
