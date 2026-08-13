"""Burn a text watermark into the bottom-right corner of the swapped output."""
from __future__ import annotations

import io
import logging
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger("whatif.watermark")

WATERMARK_TEXT = os.getenv("WATERMARK_TEXT", "Created by AI")
MARGIN_FRAC = 0.02
# Printer leaves ~4 mm unprinted on the right; inset watermark so it stays visible.
PRINT_BORDER_MM = float(os.getenv("WATERMARK_PRINT_BORDER_MM", "4"))
PRINT_WIDTH_MM = float(os.getenv("WATERMARK_PRINT_WIDTH_MM", "152"))
FONT_SIZE_FRAC = 0.035
FONT_MIN = 14

_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    log.warning("no truetype font found; using default bitmap font")
    return ImageFont.load_default()


def burn_watermark(png_bytes, opacity: float = 1.0) -> bytes:
    """Composite watermark text into the bottom-right corner."""
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    w, h = img.size

    font_size = max(FONT_MIN, int(min(w, h) * FONT_SIZE_FRAC))
    font = _load_font(font_size)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    mx = int(w * (MARGIN_FRAC + PRINT_BORDER_MM / PRINT_WIDTH_MM))
    my = int(h * MARGIN_FRAC)

    bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = w - tw - mx
    y = h - th - my

    stroke_w = max(1, font_size // 16)
    draw.text(
        (x, y),
        WATERMARK_TEXT,
        font=font,
        fill=(255, 255, 255, 255),
        stroke_width=stroke_w,
        stroke_fill=(0, 0, 0, 255),
    )

    out = Image.alpha_composite(img, overlay)

    buf = io.BytesIO()
    out.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()
