"""Short-lived upload sessions so a phone can POST a portrait while the booth polls."""
from __future__ import annotations

import json
import logging
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from threading import Lock
from urllib.parse import urlencode

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from .ethics import validate_face_upload
from .swap import perform_swap
from .watermark import burn_watermark

log = logging.getLogger("whatif.upload_session")

SESSION_TTL_SECONDS = int(os.getenv("UPLOAD_SESSION_TTL_SECONDS", "900"))
SESSION_ROOT = Path(
    os.getenv("UPLOAD_SESSION_DIR", str(Path(tempfile.gettempdir()) / "whatif-upload-sessions"))
).resolve()


class SessionStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"
    expired = "expired"


@dataclass
class UploadSession:
    id: str
    source_id: str
    status: SessionStatus
    created_at: float
    expires_at: float
    error: str | None = None
    result_png: bytes | None = field(default=None, repr=False)


_lock = Lock()


class CreateSessionBody(BaseModel):
    source_id: str


class SessionStatusResponse(BaseModel):
    session_id: str
    source_id: str
    status: SessionStatus
    expires_at: float
    mobile_upload_url: str
    error: str | None = None


router = APIRouter(prefix="/api/upload-sessions", tags=["upload-sessions"])


def public_base_url() -> str:
    for key in ("PUBLIC_BASE_URL", "NEXT_PUBLIC_PUBLIC_URL"):
        value = os.getenv(key, "").strip().rstrip("/")
        if value:
            return value
    return ""


def build_mobile_upload_url(session_id: str, source_id: str) -> str:
    query = urlencode({"session": session_id, "source": source_id})
    path = f"/mobile-upload?{query}"
    base = public_base_url()
    return f"{base}{path}" if base else path


def _session_dir(session_id: str) -> Path:
    return SESSION_ROOT / session_id


def _resolve_source_path(gallery_dir: Path, source_id: str) -> Path:
    candidates = [
        gallery_dir / f"{source_id}.jpg",
        gallery_dir / f"{source_id}.jpeg",
        gallery_dir / f"{source_id}.png",
        gallery_dir / f"{source_id}.webp",
    ]
    source_path = next((p for p in candidates if p.is_file()), None)
    if source_path is None:
        raise HTTPException(404, f"Unknown portrait id: {source_id}")
    return source_path


def _to_response(session: UploadSession) -> SessionStatusResponse:
    return SessionStatusResponse(
        session_id=session.id,
        source_id=session.source_id,
        status=session.status,
        expires_at=session.expires_at,
        mobile_upload_url=build_mobile_upload_url(session.id, session.source_id),
        error=session.error,
    )


def _save_session(session: UploadSession) -> None:
    directory = _session_dir(session.id)
    directory.mkdir(parents=True, exist_ok=True)
    meta = {
        "id": session.id,
        "source_id": session.source_id,
        "status": session.status.value,
        "created_at": session.created_at,
        "expires_at": session.expires_at,
        "error": session.error,
    }
    tmp_meta = directory / "meta.json.tmp"
    tmp_meta.write_text(json.dumps(meta), encoding="utf-8")
    tmp_meta.replace(directory / "meta.json")
    if session.result_png is not None:
        (directory / "result.png").write_bytes(session.result_png)


def _load_session(session_id: str) -> UploadSession | None:
    directory = _session_dir(session_id)
    meta_path = directory / "meta.json"
    if not meta_path.is_file():
        return None

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    session = UploadSession(
        id=meta["id"],
        source_id=meta["source_id"],
        status=SessionStatus(meta["status"]),
        created_at=float(meta["created_at"]),
        expires_at=float(meta["expires_at"]),
        error=meta.get("error"),
    )
    result_path = directory / "result.png"
    if result_path.is_file():
        session.result_png = result_path.read_bytes()

    if session.status not in (SessionStatus.ready, SessionStatus.failed) and time.time() > session.expires_at:
        session.status = SessionStatus.expired
        _save_session(session)
    return session


def _get_session(session_id: str) -> UploadSession | None:
    with _lock:
        return _load_session(session_id)


def _set_session(session: UploadSession) -> None:
    with _lock:
        _save_session(session)


@router.post("", response_model=SessionStatusResponse)
async def create_session(body: CreateSessionBody):
    from .main import GALLERY_DIR

    source_id = body.source_id.strip()
    _resolve_source_path(GALLERY_DIR, source_id)

    now = time.time()
    session = UploadSession(
        id=uuid.uuid4().hex,
        source_id=source_id,
        status=SessionStatus.pending,
        created_at=now,
        expires_at=now + SESSION_TTL_SECONDS,
    )
    _set_session(session)
    log.info("upload session created id=%s source_id=%s", session.id, session.source_id)
    return _to_response(session)


@router.get("/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    session = _get_session(session_id)
    if session is None:
        raise HTTPException(404, "Upload session not found")
    return _to_response(session)


@router.post("/{session_id}/face")
async def upload_face(
    session_id: str,
    face: UploadFile = File(...),
):
    """Mobile client uploads a portrait; booth polls until status is ready."""
    from .main import GALLERY_DIR

    session = _get_session(session_id)
    if session is None:
        raise HTTPException(404, "Upload session not found")
    if session.status == SessionStatus.expired:
        raise HTTPException(410, "Upload session expired")
    if session.status in (SessionStatus.processing, SessionStatus.ready):
        raise HTTPException(409, "Portrait already received for this session")

    face_bytes = await face.read()
    validate_face_upload(face_bytes, face.content_type or "")

    session.status = SessionStatus.processing
    session.error = None
    _set_session(session)

    source_path = _resolve_source_path(GALLERY_DIR, session.source_id)
    log.info(
        "upload session face id=%s source_id=%s upload_size=%d",
        session.id,
        session.source_id,
        len(face_bytes),
    )

    try:
        swapped = perform_swap(str(source_path), face_bytes, job_id=f"upload-{session.id[:8]}")
        try:
            watermarked = burn_watermark(swapped)
        except Exception:
            log.exception("watermark failed for session %s; returning original", session.id)
            watermarked = swapped
        session.result_png = watermarked
        session.status = SessionStatus.ready
    except ValueError as e:
        session.status = SessionStatus.failed
        session.error = str(e)
        log.warning("upload session swap failed id=%s: %s", session.id, e)
        raise HTTPException(400, str(e))
    except Exception:
        session.status = SessionStatus.failed
        session.error = "Swap engine crashed"
        log.exception("upload session swap crashed id=%s", session.id)
        raise HTTPException(500, "Swap engine crashed")
    finally:
        _set_session(session)

    return {"status": session.status.value}


@router.get("/{session_id}/result")
async def get_session_result(session_id: str):
    session = _get_session(session_id)
    if session is None:
        raise HTTPException(404, "Upload session not found")
    if session.status == SessionStatus.expired:
        raise HTTPException(410, "Upload session expired")
    if session.status == SessionStatus.failed:
        raise HTTPException(400, session.error or "Swap failed")
    if session.status != SessionStatus.ready or not session.result_png:
        raise HTTPException(409, "Result not ready yet")

    return Response(
        content=session.result_png,
        media_type="image/png",
        headers={
            "X-WhatIf-Job": f"upload-{session_id[:8]}",
            "X-WhatIf-Watermarked": "1",
        },
    )
