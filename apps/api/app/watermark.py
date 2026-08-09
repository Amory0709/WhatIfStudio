"""Burn the SLB logo into swapped output as a small corner badge (10px wide)."""
from __future__ import annotations

import io
import os
from pathlib import Path

from PIL import Image

API_DIR = Path(__file__).resolve().parent.parent
LOGO_PATH = Path(os.getenv("WATERMARK_LOGO", str(API_DIR / "assets" / "slb-logo.png")))
# Pixels darker than this become transparent (chroma-key the black bg).
KEY_THRESHOLD = 32

# The user asked for the logo to be tiny (10px wide). Keep an aspect-ratio
# proportional to the source PNG (905 x 644 ≈ 1.405:1).
WATERMARK_W_PX = 10


def _load_logo():
    if LOGO_PATH.exists():
        logo = Image.open(LOGO_PATH).convert("RGBA")
    else:
        logo = Image.new("RGBA", (WATERMARK_W_PX, WATERMARK_W_PX), (0, 0, 0, 0))

    ratio = WATERMARK_W_PX / logo.width
    target_h = max(1, int(logo.height * ratio))
    logo = logo.resize((WATERMARK_W_PX, target_h), Image.LANCZOS)

    # Chroma-key near-black pixels to transparent.
    px = logo.load()
    w, h = logo.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r <= KEY_THRESHOLD and g <= KEY_THRESHOLD and b <= KEY_THRESHOLD:
                px[x, y] = (0, 0, 0, 0)
    return logo


def burn_watermark(png_bytes, opacity=0.95):
    """Composite the SLB logo into the bottom-right corner of the swapped PNG.

    Logo is a fixed 10px wide badge. Margin = 16px from each edge.
    """
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    w, h = img.size

    logo = _load_logo()
    lw, lh = logo.size

    if opacity < 1.0:
        a = logo.split()[-1].point(lambda p: int(p * opacity))
        logo.putalpha(a)

    margin = 16
    pos = (w - lw - margin, h - lh - margin)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay.paste(logo, pos, logo)
    out = Image.alpha_composite(img, overlay)

    buf = io.BytesIO()
    out.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()
