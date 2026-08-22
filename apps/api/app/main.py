"""FastAPI app for WhatIfStudio face-swap service.

In production (Hugging Face Spaces / Docker) this single process serves BOTH:
  - the JSON / image API under /api/* and /health
  - the static Next.js export under /

Both come out of one port (default 7860) on the same origin, so the browser
can hit `/api/swap` directly with no proxy / CORS ceremony. In local dev,
leave WEB_OUT_DIR unset and run `next dev` on :3000 separately.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .booth_pipeline import booth_settings
from .diagnose_selfie import router as diagnose_selfie_router
from .ethics import validate_face_upload
from .print import router as print_router
from .swap import perform_swap
from .upload_session import router as upload_session_router
from .swap_models import list_models, resolve_default_model, resolve_model_for_request
from .watermark import burn_watermark

log = logging.getLogger("whatif")
logging.basicConfig(level=logging.INFO)

# Paths — all env-configurable so the image works in Docker AND on a dev box.
# Defaults match the Dockerfile layout (see Dockerfile), with a monorepo
# fallback for local dev when GALLERY_DIR is unset (common on Windows).
def _default_gallery_dir() -> Path:
    docker = Path("/app/web_out/gallery")
    if docker.is_dir():
        return docker
    local = Path(__file__).resolve().parents[2] / "web" / "public" / "gallery"
    if local.is_dir():
        return local
    return docker


GALLERY_DIR = Path(os.environ.get("GALLERY_DIR", str(_default_gallery_dir()))).resolve()
WEB_OUT_DIR = Path(os.environ.get("WEB_OUT_DIR", "/app/web_out")).resolve()

app = FastAPI(title="WhatIf Studio API", version="0.1.0")

# CORS: in production we serve same-origin so this is moot. In dev with the
# Next.js dev server on :3000 talking to FastAPI on :8000, set
# ALLOWED_ORIGIN="http://localhost:3000,http://127.0.0.1:3000".
_env_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGIN", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_env_origins or ["*"],
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/config")
async def public_config():
    from .upload_session import public_base_url

    return {"public_base_url": public_base_url()}


@app.get("/api/swap/models")
async def swap_models():
    """List swap models and booth pipeline tuning (prototype defaults)."""
    booth = booth_settings()
    return {
        **booth,
        "default": resolve_default_model(),
        "face_shape_model": "hififace_256",
        "models": list_models(),
    }


@app.post("/api/swap")
async def swap(
    source_id: str = Form(...),
    face: UploadFile = File(...),
    model: str = Form(default=""),
    transfer_face_shape: str = Form(default=""),
):
    """Composite the user's face onto a fictional gallery portrait."""
    face_bytes = await face.read()
    validate_face_upload(face_bytes, face.content_type or "")

    candidates = [
        GALLERY_DIR / f"{source_id}.jpg",
        GALLERY_DIR / f"{source_id}.jpeg",
        GALLERY_DIR / f"{source_id}.png",
        GALLERY_DIR / f"{source_id}.webp",
    ]
    source_path = next((p for p in candidates if p.is_file()), None)
    if source_path is None:
        raise HTTPException(404, f"Unknown portrait id: {source_id}")

    shape = transfer_face_shape.strip().lower() in ("1", "true", "yes")
    model_id = resolve_model_for_request(model or None, transfer_face_shape=shape)
    booth = booth_settings()
    log.info(
        "swap: source_id=%s model=%s face_shape=%s pipeline=%s source_weight=%s preserve_expr=%s source_path=%s upload_size=%d",
        source_id,
        model_id,
        shape,
        booth["pipeline"],
        booth["source_weight"],
        booth["preserve_expression"],
        source_path,
        len(face_bytes),
    )

    try:
        swapped = perform_swap(
            str(source_path),
            face_bytes,
            job_id="swap",
            model=model or None,
            transfer_face_shape=shape,
        )
    except ValueError as e:
        log.warning("swap failed: %s", e)
        raise HTTPException(400, str(e))
    except Exception:
        log.exception("swap crashed")
        raise HTTPException(500, "Swap engine crashed")

    try:
        watermarked = burn_watermark(swapped)
    except Exception:
        log.exception("watermark failed; returning original")
        watermarked = swapped

    return Response(
        content=watermarked,
        media_type="image/png",
        headers={
            "X-WhatIf-Job": "swap",
            "X-WhatIf-Watermarked": "1",
            "X-WhatIf-Model": model_id,
            "X-WhatIf-Mode": "facefusion",
            "X-WhatIf-Pipeline": str(booth["pipeline"]),
            "X-WhatIf-Source-Weight": str(booth["source_weight"]),
            "X-WhatIf-Preserve-Expression": str(booth["preserve_expression"]),
        },
    )


# ---------------------------------------------------------------------------
# Booth printer bridge — see apps/api/app/print.py for details.
# Mounted BEFORE the static fallback so /api/print/* is never 404'd.
# ---------------------------------------------------------------------------
app.include_router(print_router)
app.include_router(upload_session_router)
app.include_router(diagnose_selfie_router)


# ---------------------------------------------------------------------------
# Static serving for the Next.js export (apps/web/out/).
# Mounted AFTER /api/* so API routes always win.
# ---------------------------------------------------------------------------

class StaticWithFallback:
    """Starlette-compatible ASGI app: serves files from `directory`, but
    rewrites pathless segment requests like `/swap/amber-1` to
    `/swap/amber-1.html` (Next.js static export layout) and falls back to
    `index.html` for unknown SPA paths.
    """

    def __init__(self, directory: str):
        self.directory = Path(directory)
        self.static = StaticFiles(directory=directory, html=False)
        self.index_html = self.directory / "index.html"

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.static(scope, receive, send)

        path = (scope.get("path") or "/").rstrip("/") or "/"
        rel = path.lstrip("/")

        # Try as a direct file
        if (self.directory / rel).is_file():
            return await self.static(scope, receive, send)

        # Try `*.html` (Next.js places pre-rendered pages under .html)
        html_path = self.directory / (rel + ".html")
        if html_path.is_file():
            scope = dict(scope)
            scope["path"] = rel + ".html"
            return await self.static(scope, receive, send)

        # No extension → SPA fallback to index.html
        last = rel.rsplit("/", 1)[-1]
        if "." not in last and self.index_html.is_file():
            scope = dict(scope)
            scope["path"] = "index.html"
            return await self.static(scope, receive, send)

        # Otherwise let StaticFiles emit its 404
        return await self.static(scope, receive, send)


if WEB_OUT_DIR.is_dir():
    log.info("serving static web from %s", WEB_OUT_DIR)
    app.mount("/", StaticWithFallback(str(WEB_OUT_DIR)), name="web")
else:
    log.info("WEB_OUT_DIR=%s not present; running API-only", WEB_OUT_DIR)