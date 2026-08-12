"""Booth-mode printer bridge for the WhatIf Studio "Print" step.

Sends a watermarked portrait (uploaded by the client) to a locally-paired
CUPS printer via the `lp` command. This is the "kiosk/booth" path: the
Mac mini running the API has a Xiaomi Mi Home Photo Printer 1S (or any
other CUPS-aware 4R-capable dye-sub printer) paired at the OS level, and
`lp` finds it by queue name.

Two endpoints:
  GET  /api/print/status  — tells the frontend whether booth mode is configured.
  POST /api/print         — uploads an image, calls `lp`, returns the CUPS job id.

Configuration (all optional — endpoint returns 503 if BOOTH_PRINTER_NAME is unset):
  BOOTH_PRINTER_NAME   CUPS queue name (run `lpstat -p` to list).
  BOOTH_MEDIA          CUPS media size. Default "Custom.102x152mm" (4R = 4×6 in).
  BOOTH_COPIES         Default 1.
  BOOTH_RESIZE_DPI     Default 300. Image is upscaled when smaller than this.
  BOOTH_PRINT_TITLE    Job title shown on the printer LCD. Default "WhatIf Portrait".

NOTE: we deliberately do NOT re-run NSFW / face detection here. The upload has
already been moderated at `/api/swap` (the only place faces are accepted), so
re-running those checks would only add ~1 s to the print job. We still verify
the image is decodable and that it fits under MAX_UPLOAD_MB.
"""
from __future__ import annotations

import io
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

from .ethics import MAX_UPLOAD_MB

log = logging.getLogger("whatif")

router = APIRouter()

# 4R photo: 4 in × 6 in = 102 × 152 mm. CUPS custom media name on macOS.
DEFAULT_MEDIA = "Custom.102x152mm"
DEFAULT_DPI = 300  # dye-sub typical native resolution
DEFAULT_COPIES = 1
DEFAULT_TITLE = "WhatIf Portrait"
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v not in (None, "") else default


# lpstat -p <name> output shapes we care about:
#   "printer X is idle.  enabled since ..."        -> ready
#   "printer X is printing 'foo'.  enabled ..."    -> busy
#   "printer X is offline.  enabled since ..."     -> offline
#   "printer X disabled since ... - reason REASON" -> offline (with reason)
#   rc != 0 (e.g. unknown printer, CUPS down)      -> offline
_LPSTAT_REASON_MAP = {
    "media-empty": "Paper out",
    "media-empty-warning": "Paper low",
    "media-jam": "Paper jam",
    "cover-open": "Cover open",
    "toner-empty": "Toner empty",
    "marker-supply-empty": "Ink empty",
    "paused": "Paused",
    "error": "Error",
    "shutdown": "Shutting down",
}


def _parse_lpstat(out: str) -> dict:
    """Parse a successful lpstat -p <name> line into a status dict.

    Returns {state, message, connected}. Caller handles lpstat's own
    failure modes (rc != 0, FileNotFoundError, timeout).
    """
    out = (out or "").strip()
    if not out:
        return {"state": "offline", "message": "No response", "connected": False}

    low = out.lower()
    if "is idle" in low:
        return {"state": "ready", "message": "Ready", "connected": True}
    if "is printing" in low or "now printing" in low:
        return {"state": "busy", "message": "Printing…", "connected": True}
    if "is offline" in low:
        return {"state": "offline", "message": "Offline", "connected": False}
    if "disabled" in low:
        m = re.search(r"reason\s+([^\.\n]+)", out)
        if m:
            reason = m.group(1).strip()
            return {
                "state": "offline",
                "message": _LPSTAT_REASON_MAP.get(
                    reason, reason.replace("-", " ").title()
                ),
                "connected": False,
            }
        return {"state": "offline", "message": "Disabled", "connected": False}
    if "stopped" in low:
        return {"state": "error", "message": "Stopped", "connected": False}
    if "error" in low:
        return {"state": "error", "message": "Error", "connected": False}
    return {"state": "offline", "message": out[:60], "connected": False}


def _lpstat(name: str) -> dict:
    """Run lpstat -p <name> and parse the printer state.

    Returns {state, message, connected} in every case. Never raises —
    any subprocess or parsing error degrades to {state: "offline", ...}.
    """
    if shutil.which("lpstat") is None:
        return {
            "state": "error",
            "message": "lpstat not available",
            "connected": False,
        }
    try:
        proc = subprocess.run(
            ["lpstat", "-p", name],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return {"state": "error", "message": "lpstat timeout", "connected": False}
    except Exception as e:
        return {"state": "error", "message": str(e)[:60], "connected": False}

    if proc.returncode != 0:
        # lpstat failed. Don't leak the raw stderr to the UI — translate
        # the common cases ("unknown destination") into operator-friendly
        # hints and log the raw output for debugging.
        raw = (proc.stderr or proc.stdout or "").strip()
        low = raw.lower()
        if "invalid destination" in low or "unknown" in low:
            msg = "Printer not paired in CUPS"
        elif "permission" in low:
            msg = "lpstat permission denied"
        elif raw:
            msg = "lpstat error"
        else:
            msg = "Unknown printer"
        log.warning("lpstat -p %s failed (rc=%s): %s", name, proc.returncode, raw)
        return {"state": "offline", "message": msg, "connected": False}

    return _parse_lpstat(proc.stdout)


@router.get("/api/print/status")
async def status() -> dict:
    """Tell the frontend whether booth mode is configured AND reachable.

    The web client polls this endpoint every 5 s while on the print step
    to render a live status pill above the "Print Here" button. When
    BOOTH_PRINTER_NAME is unset we skip the lpstat call entirely (no
    point probing a printer that doesn't exist).
    """
    name = _env("BOOTH_PRINTER_NAME", "")
    base = {
        "available": bool(name),
        "printer": name or None,
        "media": _env("BOOTH_MEDIA", DEFAULT_MEDIA),
        "copies": int(_env("BOOTH_COPIES", str(DEFAULT_COPIES))),
    }
    if not name:
        return {**base, "state": "offline", "message": "Not configured", "connected": False}
    return {**base, **_lpstat(name)}


@router.post("/api/print")
async def booth_print(
    image: UploadFile = File(...),
    title: Optional[str] = Form(None),
) -> JSONResponse:
    name = _env("BOOTH_PRINTER_NAME", "")
    if not name:
        raise HTTPException(
            503,
            "Booth printer not configured. Set BOOTH_PRINTER_NAME in the "
            "service environment, then restart the container.",
        )

    if shutil.which("lp") is None:
        raise HTTPException(
            503,
            "`lp` not found in PATH. Install CUPS client tools "
            "(macOS: ships with the OS; Linux: `apt install cups-client`).",
        )

    media = _env("BOOTH_MEDIA", DEFAULT_MEDIA)
    n = int(_env("BOOTH_COPIES", str(DEFAULT_COPIES)))
    job_title = (title or _env("BOOTH_PRINT_TITLE", DEFAULT_TITLE))[:64]
    target_dpi = int(_env("BOOTH_RESIZE_DPI", str(DEFAULT_DPI)))

    blob = await image.read()
    if len(blob) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"Upload exceeds {MAX_UPLOAD_MB}MB")
    if image.content_type and image.content_type not in ALLOWED_MIME:
        raise HTTPException(415, f"Unsupported media type: {image.content_type}")

    # Decode once up front so we can both validate and resize.
    try:
        img = Image.open(io.BytesIO(blob))
        img.load()
    except Exception:
        raise HTTPException(400, "Unreadable image")

    if img.mode != "RGB":
        img = img.convert("RGB")

    # 4R at 300 DPI = 1200 × 1800. Up-res only when the source is clearly too
    # small (don't bloat already-large uploads).
    target_w, target_h = 4 * target_dpi, 6 * target_dpi
    if img.size[0] < target_w and img.size[1] < target_h:
        img = img.resize((target_w, target_h), Image.LANCZOS)

    tmp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        img.save(
            tmp_path,
            "JPEG",
            quality=95,
            dpi=(target_dpi, target_dpi),
            subsampling=0,  # 4:4:4 — no chroma blur for photo prints
        )

        cmd = [
            "lp",
            "-d", name,
            "-t", job_title,
            "-n", str(n),
            "-o", f"media={media}",
            "-o", "fit-to-page",
            "-o", "print-quality=5",  # CUPS quality 5 = best (dye-sub photo)
            str(tmp_path),
        ]
        log.info("lp: %s", " ".join(cmd))
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            log.error(
                "lp failed rc=%d stdout=%r stderr=%r",
                proc.returncode,
                proc.stdout,
                proc.stderr,
            )
            raise HTTPException(
                500,
                f"Printer rejected job: "
                f"{(proc.stderr or proc.stdout or 'unknown').strip()}",
            )

        # `lp` prints e.g. "request id is Mi_Printer-42 (1 file(s))" on success.
        job_id = ""
        for line in (proc.stdout or "").splitlines():
            if "request id is" in line:
                job_id = line.split("request id is", 1)[1].strip().split(" ")[0]
                break

        return JSONResponse(
            {
                "ok": True,
                "printer": name,
                "media": media,
                "copies": n,
                "job_id": job_id,
            }
        )
    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        log.exception("lp timed out")
        raise HTTPException(504, "Printer did not respond in time")
    except Exception as e:
        log.exception("booth print failed")
        raise HTTPException(500, f"Print failed: {e}")
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass