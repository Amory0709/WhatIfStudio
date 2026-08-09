"""Burn the SLB logo into swapped output as a tiny 10px corner badge."""
from __future__ import annotations

import io
import os
from pathlib import Path

from PIL import Image

API_DIR = Path(__file__).resolve().parent.parent
# Pre-baked 100x70 RGBA badge (chroma-keyed at build time). Loading this and
# resizing to 10x7 at composite time avoids the destructive 40:1 downsample
# we used to get when going from the 400x280 source directly to 10x7.
LOGO_PATH = Path(os.getenv("WATERMARK_LOGO", str(API_DIR / "assets" / "slb-logo.png")))
BADGE_PATH = Path(os.getenv("WATERMARK_BADGE", str(API_DIR / "assets" / "slb-badge-rgba.png")))

WATERMARK_W_PX = 10


def _load_badge():
    if BADGE_PATH.exists():
        return Image.open(BADGE_PATH).convert("RGBA")
    # Fallback: load + chroma-key on the fly
    KEY_THRESHOLD = 32
    logo = Image.open(LOGO_PATH).convert("RGBA")
    px = logo.load()
    for y in range(logo.height):
        for x in range(logo.width):
            r, g, b, a = px[x, y]
            if r <= KEY_THRESHOLD and g <= KEY_THRESHOLD and b <= KEY_THRESHOLD:
                px[x, y] = (0, 0, 0, 0)
    return logo


def burn_watermark(png_bytes, opacity=0.95):
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    w, h = img.size

    badge = _load_badge()
    ratio = WATERMARK_W_PX / badge.width
    target_h = max(1, int(badge.height * ratio))
    badge = badge.resize((WATERMARK_W_PX, target_h), Image.LANCZOS)

    if opacity < 1.0:
        a = badge.split()[-1].point(lambda p: int(p * opacity))
        badge.putalpha(a)

    margin = 16
    pos = (w - WATERMARK_W_PX - margin, h - target_h - margin)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay.paste(badge, pos, badge)
    out = Image.alpha_composite(img, overlay)

    buf = io.BytesIO()
    out.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()
