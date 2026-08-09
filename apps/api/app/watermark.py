"""Burn the SLB logo into swapped output as a visible watermark."""
from __future__ import annotations

import io
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

API_DIR = Path(__file__).resolve().parent.parent
LOGO_PATH = Path(os.getenv("WATERMARK_LOGO", str(API_DIR / "assets" / "slb-logo.png")))


def _load_logo(size: int) -> Image.Image:
    if LOGO_PATH.exists():
        logo = Image.open(LOGO_PATH).convert("RGBA")
    else:
        logo = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(logo)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size // 3)
        except Exception:
            try:
                font = ImageFont.truetype("arial.ttf", size // 3)
            except Exception:
                font = ImageFont.load_default()
        d.text((10, 10), "SLB", fill=(255, 255, 255, 235), font=font)
    return logo


def burn_watermark(png_bytes: bytes, opacity: float = 0.85) -> bytes:
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    w, h = img.size

    target = max(64, int(w * 0.18))
    logo = _load_logo(target).resize((target, target), Image.LANCZOS)

    if opacity < 1.0:
        a = logo.split()[-1].point(lambda p: int(p * opacity))
        logo.putalpha(a)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay.paste(logo, (w - target - 24, 24), logo)
    out = Image.alpha_composite(img, overlay)

    buf = io.BytesIO()
    out.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()
