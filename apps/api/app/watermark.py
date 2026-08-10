"""Burn the SLB logo into the bottom-right corner of the swapped output.

The logo is read from apps/api/assets/slb_logo.svg (brand-blue #0014dc
fill on transparent background) and rasterised via cairosvg. We then
hard-threshold the alpha channel so the watermark is fully opaque, no
soft edges, no compositing transparency: every blue pixel is alpha=255,
every background pixel is alpha=0. That keeps the burned mark looking
like a printed brand stamp on the photo, not a translucent overlay.
"""
from __future__ import annotations

import io
import logging
import os
from pathlib import Path

from PIL import Image

log = logging.getLogger("whatif.watermark")

API_DIR = Path(__file__).resolve().parent.parent
LOGO_PATH = Path(
    os.getenv("WATERMARK_LOGO", str(API_DIR / "assets" / "slb_logo.svg"))
)

# Badge size: 30% of the long edge (bold brand stamp on the print).
BADGE_FRAC = 0.30
BADGE_MIN = 100
BADGE_MARGIN_FRAC = 0.02  # 2% of each photo dimension

# Render the SVG at this width so the final downscale is crisp.
RASTER_W = 4096


def _rasterize_svg(path: Path) -> Image.Image:
    """Convert an SVG to an RGBA Pillow image using cairosvg."""
    import cairosvg  # lazy: only fails if cairo is missing at use time

    png_bytes = cairosvg.svg2png(url=str(path), output_width=RASTER_W)
    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")


def _load_logo_opaque() -> Image.Image:
    """Open the SLB logo (SVG or PNG), crop transparent edges, force alpha to 0 or 255."""
    suffix = LOGO_PATH.suffix.lower()
    if suffix == ".svg":
        logo = _rasterize_svg(LOGO_PATH)
    else:
        logo = Image.open(LOGO_PATH).convert("RGBA")

    alpha = logo.split()[-1]
    alpha = alpha.point(lambda p: 255 if p >= 128 else 0)
    logo.putalpha(alpha)

    bbox = logo.getbbox()
    if bbox:
        logo = logo.crop(bbox)
    return logo


def burn_watermark(png_bytes, opacity: float = 1.0) -> bytes:
    """Composite the SLB logo into the bottom-right at 70% of the long edge."""
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    w, h = img.size

    try:
        glyph = _load_logo_opaque()
    except FileNotFoundError:
        log.warning("watermark logo not found at %s; skipping", LOGO_PATH)
        return png_bytes
    except Exception:
        log.exception("watermark render failed; returning original image")
        return png_bytes

    if glyph.width == 0 or glyph.height == 0:
        return png_bytes

    badge_w = max(BADGE_MIN, int(max(w, h) * BADGE_FRAC))
    ratio = badge_w / glyph.width
    target_h = max(1, int(glyph.height * ratio))
    glyph = glyph.resize((badge_w, target_h), Image.LANCZOS)

    mx = int(w * BADGE_MARGIN_FRAC)
    my = int(h * BADGE_MARGIN_FRAC)
    pos = (w - badge_w - mx, h - target_h - my)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay.paste(glyph, pos, glyph)
    out = Image.alpha_composite(img, overlay)

    buf = io.BytesIO()
    out.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()
