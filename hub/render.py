"""Renders 96x96 (configurable) key images with Pillow.
If an icon file is missing, generates a colored tile with the app's initial,
so everything works before you've collected icons.
"""
import os
import hashlib
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_DIR = os.path.join(ROOT, "icons")
KEY_SIZE = 96  # Mirabox N3 keys accept ~96x96; adapter rescales if needed

_font_cache = {}


def _font(size):
    if size not in _font_cache:
        try:
            _font_cache[size] = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        except Exception:
            _font_cache[size] = ImageFont.load_default()
    return _font_cache[size]


def _color_for(name):
    h = hashlib.md5(name.encode()).digest()
    return (80 + h[0] % 150, 80 + h[1] % 150, 80 + h[2] % 150)


def _base(bg=(20, 20, 24)):
    return Image.new("RGB", (KEY_SIZE, KEY_SIZE), bg)


def _center_text(img, text, size, fill=(240, 240, 240), dy=0):
    d = ImageDraw.Draw(img)
    f = _font(size)
    box = d.textbbox((0, 0), text, font=f)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((KEY_SIZE - w) / 2, (KEY_SIZE - h) / 2 + dy - box[1]), text,
           font=f, fill=fill)


def _load_icon(icon_name, label):
    if icon_name:
        path = os.path.join(ICON_DIR, icon_name)
        if os.path.exists(path):
            img = Image.open(path).convert("RGB")
            return img.resize((KEY_SIZE, KEY_SIZE))
    # generated placeholder tile
    img = _base(_color_for(label))
    _center_text(img, (label or "?")[0].upper(), 48, dy=-8)
    return img


def render_app_key(profile):
    img = _load_icon(profile.get("icon"), profile["name"])
    d = ImageDraw.Draw(img)
    d.rectangle([0, KEY_SIZE - 22, KEY_SIZE, KEY_SIZE], fill=(0, 0, 0))
    label = profile.get("label", profile["name"])[:12]
    f = _font(13)
    box = d.textbbox((0, 0), label, font=f)
    d.text(((KEY_SIZE - (box[2] - box[0])) / 2, KEY_SIZE - 19), label,
           font=f, fill=(255, 255, 255))
    return img


def render_action_key(keydef, recording=False):
    label = keydef.get("label", keydef.get("action", ""))
    if keydef.get("action") == "voice_toggle":
        img = _base((160, 30, 30) if recording else (30, 30, 36))
        _center_text(img, "REC" if recording else "MIC", 26, dy=-10)
        _center_text(img, "recording..." if recording else "push to talk", 11, dy=26)
        return img
    img = _load_icon(keydef.get("icon"), label)
    if "icon" not in keydef:
        img = _base((36, 36, 44))
        _center_text(img, label[:10], 16)
    return img


def render_blank():
    return _base((12, 12, 14))
