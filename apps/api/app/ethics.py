"""Ethics gate for face uploads.

Refuses:
- non-image uploads
- files larger than MAX_UPLOAD_MB
- images flagged by opennsfw2 as NSFW
- images with no detectable face
"""
from __future__ import annotations

import io
import logging
import os
from typing import Final, Optional

from fastapi import HTTPException
from PIL import Image

MAX_UPLOAD_MB: Final = int(os.getenv("MAX_UPLOAD_MB", "10"))
ALLOWED_MIME = {"image/jpeg", "image/png", "image/heic", "image/webp"}

log = logging.getLogger("whatif")


def validate_face_upload(blob: bytes, content_type: str) -> None:
    if len(blob) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"Upload exceeds {MAX_UPLOAD_MB}MB")

    if content_type and content_type not in ALLOWED_MIME:
        raise HTTPException(415, f"Unsupported media type: {content_type}")

    try:
        img = Image.open(io.BytesIO(blob))
        img.verify()
    except Exception:
        raise HTTPException(400, "Unreadable image")

    _check_nsfw(blob)
    _check_face(blob)


def _check_nsfw(blob: bytes) -> None:
    try:
        import numpy as np
        from opennsfw2 import predict_image
        arr = np.array(Image.open(io.BytesIO(blob)).convert("RGB"))
        nsfw_prob, _ = predict_image(arr)
        if nsfw_prob > 0.6:
            raise HTTPException(400, "Image failed content moderation")
    except HTTPException:
        raise
    except Exception:
        log.warning("NSFW model unavailable, skipping moderation")


def _check_face(blob: bytes) -> None:
    try:
        import cv2
        import numpy as np
        from insightface.app import FaceAnalysis
        app = _get_face_app()
        if app is None:
            return
        arr = cv2.imdecode(np.frombuffer(blob, np.uint8), cv2.IMREAD_COLOR)
        if arr is None or not app.get(arr):
            raise HTTPException(400, "No face detected in upload")
    except HTTPException:
        raise
    except Exception:
        log.warning("Face detector unavailable, skipping pre-check")


_FACE_APP_SINGLETON: Optional[object] = None


def _get_face_app():
    global _FACE_APP_SINGLETON
    if _FACE_APP_SINGLETON is not None:
        return _FACE_APP_SINGLETON
    try:
        from insightface.app import FaceAnalysis
        _FACE_APP_SINGLETON = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        _FACE_APP_SINGLETON.prepare(ctx_id=-1, det_size=(320, 320))
    except Exception:
        _FACE_APP_SINGLETON = None
    return _FACE_APP_SINGLETON
