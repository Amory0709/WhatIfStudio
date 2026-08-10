"""FastAPI app for WhatIfStudio face-swap service."""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .ethics import validate_face_upload
from .swap import perform_swap
from .watermark import burn_watermark

log = logging.getLogger("whatif")
logging.basicConfig(level=logging.INFO)

# __file__ = apps/api/app/main.py -> parent x4 = repo root (whatifstudio/)
ROOT_DIR = Path(__file__).resolve().parents[3]
GALLERY_DIR = ROOT_DIR / "apps" / "web" / "public" / "gallery"

app = FastAPI(title="WhatIf Studio API", version="0.1.0")

_default_dev_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://[::1]:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
_env_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGIN", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_env_origins or _default_dev_origins,
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/swap")
async def swap(source_id: str = Form(...), face: UploadFile = File(...)):
    """Composite the user's face onto a fictional gallery portrait."""
    face_bytes = await face.read()
    validate_face_upload(face_bytes, face.content_type or "")

    candidates = [
        GALLERY_DIR / f"{source_id}.jpg",
        GALLERY_DIR / f"{source_id}.jpeg",
        GALLERY_DIR / f"{source_id}.png",
        GALLERY_DIR / f"{source_id}.webp",
    ]
    log.info("swap lookup: GALLERY_DIR=%s source_id=%s candidates=%s exists=%s",
             GALLERY_DIR, source_id, [str(c) for c in candidates], [c.exists() for c in candidates])
    source_path = next((p for p in candidates if p.exists()), None)
    if not source_path:
        raise HTTPException(404, f"No artwork for id={source_id} (gallery dir={GALLERY_DIR})")

    job_id = uuid.uuid4().hex[:10]
    try:
        swapped_png = perform_swap(
            source_path=str(source_path),
            face_bytes=face_bytes,
            job_id=job_id,
        )
    except ValueError as e:
        log.warning("swap ValueError: %s", e)
        raise HTTPException(400, str(e))
    except Exception:
        log.exception("swap failed (full traceback below)")
        raise HTTPException(500, "Swap engine error")

    final = burn_watermark(swapped_png, opacity=1.0)

    return Response(
        content=final,
        media_type="image/png",
        headers={
            "X-WhatIf-Job": job_id,
            "X-WhatIf-Watermarked": "slb-1",
            "Cache-Control": "no-store",
        },
    )
