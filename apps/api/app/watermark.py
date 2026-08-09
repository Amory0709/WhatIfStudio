"""Burn the SLB logo into swapped output as a visible watermark (bottom-right)."""
from __future__ import annotations

import io
import os
from pathlib import Path

from PIL import Image

API_DIR = Path(__file__).resolve().parent.parent
LOGO_PATH = Path(os.getenv("WATERMARK_LOGO", str(API_DIR / "assets" / "slb-logo.png")))
# Pixels darker than this become transparent (chroma-key the black bg).
KEY_THRESHOLD = 32


def _load_logo(target_w):
    if LOGO_PATH.exists():
        logo = Image.open(LOGO_PATH).convert("RGBA")
        ratio = target_w / logo.width
        target_h = max(1, int(logo.height * ratio))
        logo = logo.resize((target_w, target_h), Image.LANCZOS)
    else:
        logo = Image.new("RGBA", (target_w, 1), (0, 0, 0, 0))

    px = logo.load()
    w, h = logo.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r <= KEY_THRESHOLD and g <= KEY_THRESHOLD and b <= KEY_THRESHOLD:
                px[x, y] = (0, 0, 0, 0)
    return logo


def burn_watermark(png_bytes, opacity=0.92):
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    w, h = img.size

    target_w = max(96, int(w * 0.28))
    logo = _load_logo(target_w)
    lw, lh = logo.size

    if opacity < 1.0:
        a = logo.split()[-1].point(lambda p: int(p * opacity))
        logo.putalpha(a)

    margin = max(24, int(w * 0.02))
    pos = (w - lw - margin, h - lh - margin)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay.paste(logo, pos, logo)
    out = Image.alpha_composite(img, overlay)

    buf = io.BytesIO()
    out.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()
