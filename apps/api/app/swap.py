"""Face-swap API — booth default uses Deep-Live-Cam; optional FaceFusion models."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

from .onnx_swapper import BOOTH_SOURCE_WEIGHT, ENV_SOURCE_WEIGHT, ensure_models, swap_image as facefusion_swap_image
from .swap_helpers import (
    apply_full_head_from_source,
    booth_poisson_blend,
    booth_sharpness,
    downscale_image,
    ensure_execution_providers,
    extract_face_crop,
    extract_source_face_patch,
    harmonize_face_color,
    preserve_portrait_expression,
    paste_crop_back,
    prepare_crop_for_swap,
    sharpen_crop,
    swap_output_sane,
    adaptive_soft_top_frac,
)
from .swap_models import MODELS, SwapModelId, resolve_model_for_request

ENGINE_DIR = Path(os.environ.get("WHATIF_ENGINE_DIR", ".")).resolve()
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))


def perform_swap(
    source_path: str,
    face_bytes: bytes,
    job_id: str,
    model: str | None = None,
    transfer_face_shape: bool = False,
) -> bytes:
    """Booth swap — InSwapper default; HifiFace when visitor face shape is requested."""
    _ = job_id
    model_id = resolve_model_for_request(model, transfer_face_shape=transfer_face_shape)

    if model_id == "hififace_256":
        ensure_models("hififace_256")
        return _perform_facefusion_swap(
            model_id,
            source_path,
            face_bytes,
            full_appearance=True,
        )

    if model_id == "hyperswap_256":
        ensure_models(model_id)
        return _perform_facefusion_swap(model_id, source_path, face_bytes, full_appearance=False)

    if model_id == "reswapper_256":
        ensure_models(model_id)
        return _perform_dlc_swap(model_id, source_path, face_bytes)

    os.environ[ENV_SOURCE_WEIGHT] = BOOTH_SOURCE_WEIGHT
    ensure_models("inswapper_128")
    if os.environ.get("WHATIF_HYBRID_MASK", "").strip().lower() in ("1", "true", "yes"):
        return _perform_hybrid_inswapper_swap(source_path, face_bytes)
    return _perform_facefusion_inswapper_swap(source_path, face_bytes)


def _run_dlc_on_image(
    model_id: SwapModelId,
    work_img: np.ndarray,
    face_bytes: bytes,
) -> np.ndarray:
    from modules import globals as g
    from modules import imread_unicode, imwrite_unicode
    from modules.processors.frame import face_swapper

    spec = MODELS[model_id]
    g.opacity = 1.0
    g.many_faces = False
    g.map_faces = False
    g.mouth_mask = False
    g.poisson_blend = booth_poisson_blend()
    g.sharpness = booth_sharpness()

    if g.swap_model != model_id:
        g.swap_model = model_id
        face_swapper.reset_face_swapper()
    if not face_swapper.pre_start():
        raise ValueError(
            f"Face-swap model '{model_id}' not loaded — check engine/models/ "
            f"for {', '.join(spec.model_files)}"
        )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src_face_path = tmp_path / "face.jpg"
        src_face_path.write_bytes(face_bytes)

        target_path = tmp_path / "target.png"
        if not imwrite_unicode(str(target_path), work_img):
            raise ValueError("Failed to write target frame")

        face_swapper.process_frames(
            source_path=str(src_face_path),
            temp_frame_paths=[str(target_path)],
        )

        result = imread_unicode(str(target_path))
        if result is None:
            raise ValueError("Swap produced no image")
        return result


def _finish_crop(
    swapped: np.ndarray,
    crop: np.ndarray,
    scale: float,
    *,
    source_patch: np.ndarray | None = None,
    enhanced: bool = False,
) -> np.ndarray:
    swapped = downscale_image(swapped, scale)
    swapped = sharpen_crop(swapped, strength=0.42 if enhanced else None)
    if enhanced and source_patch is not None:
        swapped = apply_full_head_from_source(swapped, source_patch)
    else:
        swapped = harmonize_face_color(swapped, crop)
    return swapped


def _perform_dlc_swap(
    model_id: SwapModelId,
    source_path: str,
    face_bytes: bytes,
) -> bytes:
    """InSwapper on face crop — enhanced with user's skin tone."""
    from modules.face_analyser import get_one_face
    from modules import imread_unicode

    ensure_execution_providers()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src_face_path = tmp_path / "face.jpg"
        src_face_path.write_bytes(face_bytes)
        source_face_img = imread_unicode(str(src_face_path))

    source_patch = None
    if source_face_img is not None:
        source_face = get_one_face(source_face_img)
        if source_face is not None:
            source_patch = extract_source_face_patch(source_face_img, source_face)

    target_img = imread_unicode(source_path)
    if target_img is None:
        raise ValueError("Failed to read gallery portrait")

    target_face = get_one_face(target_img)
    if target_face is None:
        raise ValueError("No face detected in gallery portrait")

    rect, crop = extract_face_crop(target_img, target_face)
    crop_face = get_one_face(crop) or target_face
    work_crop, scale = prepare_crop_for_swap(crop, crop_face)

    swapped = _run_dlc_on_image(model_id, work_crop, face_bytes)
    swapped = _finish_crop(
        swapped,
        crop,
        scale,
        source_patch=source_patch,
        enhanced=True,
    )
    swapped = preserve_portrait_expression(swapped, crop, crop_face)
    result = paste_crop_back(target_img, rect, swapped, crop, soft_top_frac=0.12)

    check_face = get_one_face(result) or target_face
    if not swap_output_sane(result, check_face):
        raise ValueError(
            "Swap produced a corrupted face — try a clearer front-facing photo."
        )

    ok, buf = cv2.imencode(".png", result)
    if not ok:
        raise ValueError("Failed to encode swap output")
    return buf.tobytes()


def _perform_hybrid_inswapper_swap(
    source_path: str,
    face_bytes: bytes,
) -> bytes:
    """FF box+XSeg on crop + booth harmonize, expression, paste (top_soft=0.12)."""
    return _perform_facefusion_inswapper_swap(
        source_path,
        face_bytes,
        mask_mode="facefusion",
        top_soft_frac=0.12,
    )


def _perform_facefusion_inswapper_swap(
    source_path: str,
    face_bytes: bytes,
    *,
    mask_mode: str = "ellipse",
    top_soft_frac: float | None = None,
) -> bytes:
    """FaceFusion warp/mask + InSwapper ONNX on gallery face crop."""
    from modules.face_analyser import get_one_face
    from modules import imread_unicode

    ensure_execution_providers()
    os.environ[ENV_SOURCE_WEIGHT] = BOOTH_SOURCE_WEIGHT

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src_face_path = tmp_path / "face.jpg"
        src_face_path.write_bytes(face_bytes)

        source_face_img = imread_unicode(str(src_face_path))
        target_img = imread_unicode(source_path)
        if source_face_img is None or target_img is None:
            raise ValueError("Failed to read source or target image")

        source_face = get_one_face(source_face_img)
        target_face = get_one_face(target_img)
        if source_face is None:
            raise ValueError("No face detected in uploaded photo")
        if target_face is None:
            raise ValueError("No face detected in gallery portrait")

        rect, crop = extract_face_crop(target_img, target_face)
        crop_face = get_one_face(crop) or target_face
        work_crop, scale = prepare_crop_for_swap(crop, crop_face)
        work_face = get_one_face(work_crop) or crop_face

        swapped = facefusion_swap_image(
            "inswapper_128",
            source_face_img,
            work_crop,
            source_face,
            work_face,
            full_appearance=False,
            mask_mode=mask_mode,  # type: ignore[arg-type]
        )
        swapped = _finish_crop(swapped, crop, scale, enhanced=False)
        swapped = preserve_portrait_expression(swapped, crop, crop_face)
        top_soft = top_soft_frac if top_soft_frac is not None else adaptive_soft_top_frac(crop)
        result = paste_crop_back(target_img, rect, swapped, crop, soft_top_frac=top_soft)

    check_face = get_one_face(result) or target_face
    if not swap_output_sane(result, check_face):
        raise ValueError(
            "Swap produced a corrupted face — try a clearer front-facing photo."
        )

    ok, buf = cv2.imencode(".png", result)
    if not ok:
        raise ValueError("Failed to encode swap output")
    return buf.tobytes()


def _perform_facefusion_swap(
    model_id: SwapModelId,
    source_path: str,
    face_bytes: bytes,
    *,
    full_appearance: bool = False,
) -> bytes:
    from modules.face_analyser import get_one_face
    from modules import imread_unicode

    ensure_execution_providers()

    # HifiFace — visitor head (shape + identity); high source weight.
    if full_appearance and model_id == "hififace_256":
        os.environ[ENV_SOURCE_WEIGHT] = "0.96"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src_face_path = tmp_path / "face.jpg"
        src_face_path.write_bytes(face_bytes)

        source_face_img = imread_unicode(str(src_face_path))
        target_img = imread_unicode(source_path)
        if source_face_img is None or target_img is None:
            raise ValueError("Failed to read source or target image")

        source_face = get_one_face(source_face_img)
        target_face = get_one_face(target_img)
        if source_face is None:
            raise ValueError("No face detected in uploaded photo")
        if target_face is None:
            raise ValueError("No face detected in gallery portrait")

        source_patch = extract_source_face_patch(source_face_img, source_face)

        rect, crop = extract_face_crop(target_img, target_face)
        crop_face = get_one_face(crop) or target_face
        work_crop, scale = prepare_crop_for_swap(crop, crop_face)
        work_face = get_one_face(work_crop) or crop_face

        swapped = facefusion_swap_image(
            model_id,
            source_face_img,
            work_crop,
            source_face,
            work_face,
            full_appearance=full_appearance,
        )
        swapped = _finish_crop(
            swapped,
            crop,
            scale,
            source_patch=source_patch,
            enhanced=full_appearance,
        )
        top_soft = adaptive_soft_top_frac(crop) if full_appearance else 0.0
        result = paste_crop_back(
            target_img,
            rect,
            swapped,
            crop,
            soft_top_frac=top_soft,
        )

    if not swap_output_sane(result, target_face):
        raise ValueError(
            "Swap produced a corrupted face — switch to InSwapper 128 (default) "
            "or use a clearer front-facing photo."
        )

    ok, buf = cv2.imencode(".png", result)
    if not ok:
        raise ValueError("Failed to encode swap output")
    return buf.tobytes()
