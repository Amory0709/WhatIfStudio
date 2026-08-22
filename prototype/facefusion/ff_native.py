"""PROTOTYPE — FaceFusion-style swap using in-repo ONNX + XSeg/box masks."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def _setup_env() -> None:
    os.environ.setdefault("WHATIF_ENGINE_DIR", str(ROOT / "apps" / "api" / "engine"))
    api = str(ROOT / "apps" / "api")
    if api not in sys.path:
        sys.path.insert(0, api)
    eng = os.environ["WHATIF_ENGINE_DIR"]
    if eng not in sys.path:
        sys.path.insert(0, eng)


def swap_image_ff_mask(
    source_bgr: np.ndarray,
    target_bgr: np.ndarray,
    source_face,
    target_face,
    *,
    model_id: str = "inswapper_128",
) -> np.ndarray:
    """FaceFusion mask stack on warped crop; no booth crop paste."""
    _setup_env()
    from app.face_masker import build_crop_mask, ensure_occluder
    from app.onnx_swapper import (
        ENV_SOURCE_WEIGHT,
        BOOTH_SOURCE_WEIGHT,
        _prepare_source_embedding,
        _prepare_crop,
        _normalize_output,
        _resolve_onnx_path,
        _swap_config,
        _load_session,
    )
    from app.warp_helper import paste_back, warp_face

    ensure_occluder()
    os.environ[ENV_SOURCE_WEIGHT] = BOOTH_SOURCE_WEIGHT

    cfg = _swap_config(model_id)  # type: ignore[arg-type]
    swapper_path = _resolve_onnx_path(model_id)  # type: ignore[arg-type]
    session = _load_session(swapper_path)

    crop, matrix = warp_face(target_bgr, target_face.kps, cfg.template, cfg.crop_size)
    crop_mask = build_crop_mask(crop)
    source_emb = _prepare_source_embedding(
        model_id,  # type: ignore[arg-type]
        source_face,
        target_face,
        swapper_path,
        cfg,
    )
    crop_in = _prepare_crop(crop, cfg)

    inputs: dict[str, np.ndarray] = {}
    for node in session.get_inputs():
        if node.name == "source":
            inputs[node.name] = source_emb
        elif node.name == "target":
            inputs[node.name] = crop_in
        else:
            raise ValueError(f"Unexpected ONNX input: {node.name}")

    out = session.run(None, inputs)[0]
    swapped_crop = _normalize_output(out, cfg)
    return paste_back(target_bgr, swapped_crop, crop_mask, matrix)


def perform_ff_native_swap(portrait_path: str, face_bytes: bytes) -> bytes:
    """Full gallery frame — FF masks on face region only (no SLB crop paste)."""
    _setup_env()
    from modules.face_analyser import get_one_face
    from modules import imread_unicode

    with tempfile.TemporaryDirectory() as tmp:
        face_path = Path(tmp) / "upload.jpg"
        face_path.write_bytes(face_bytes)
        source_img = imread_unicode(str(face_path))
        target_img = imread_unicode(portrait_path)
        if source_img is None or target_img is None:
            raise ValueError("Failed to read upload or portrait")

        source_face = get_one_face(source_img)
        target_face = get_one_face(target_img)
        if source_face is None:
            raise ValueError("No face in upload")
        if target_face is None:
            raise ValueError("No face in portrait")

        result = swap_image_ff_mask(source_img, target_img, source_face, target_face)

    ok, buf = cv2.imencode(".png", result)
    if not ok:
        raise ValueError("Failed to encode output")
    return buf.tobytes()
