#!/usr/bin/env python3
"""PROTOTYPE static server + /swap for camera capture demo.

Production booth: use `apps/api` main.py (`POST /api/swap`) + web DetailView.
This server is for local eval only.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[2]
PROTO = Path(__file__).resolve().parent
GALLERY = ROOT / "apps" / "web" / "public" / "gallery"

sys.path.insert(0, str(ROOT / "apps" / "api"))
os.environ.setdefault("WHATIF_ENGINE_DIR", str(ROOT / "apps" / "api" / "engine"))
os.environ.setdefault("GALLERY_DIR", str(GALLERY))

from app.ethics import validate_face_upload  # noqa: E402
from app.swap import perform_swap  # noqa: E402

app = FastAPI(title="WhatIf flux-identity prototype", docs_url=None, redoc_url=None)


def _portrait_path(portrait_id: str) -> Path | None:
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        path = GALLERY / f"{portrait_id}{ext}"
        if path.is_file():
            return path
    return None


@app.get("/api/portraits")
def list_portraits():
    data = json.loads((PROTO / "portraits-capture.json").read_text(encoding="utf-8"))
    out = []
    for item in data["portraits"]:
        pid = item["id"]
        out.append({**item, "available": _portrait_path(pid) is not None})
    return {"portraits": out}


@app.get("/gallery/{portrait_id}")
def gallery_image(portrait_id: str):
    path = _portrait_path(portrait_id)
    if path is None:
        raise HTTPException(404, f"Portrait not found: {portrait_id}")
    return FileResponse(path)


@app.post("/swap")
async def swap(portrait_id: str = Form(...), face: UploadFile = File(...)):
    source = _portrait_path(portrait_id.strip())
    if source is None:
        raise HTTPException(404, f"Portrait not found: {portrait_id}")

    face_bytes = await face.read()
    validate_face_upload(face_bytes, face.content_type or "image/jpeg")

    try:
        png = perform_swap(str(source), face_bytes, job_id="prototype-capture")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, "Swap engine crashed") from exc

    return Response(content=png, media_type="image/png")


app.mount("/", StaticFiles(directory=str(PROTO), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
