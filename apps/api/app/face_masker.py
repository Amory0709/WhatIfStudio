"""FaceFusion-style face masks (box + occlusion)."""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
import onnxruntime

from .swap_models import _engine_models_dir

log = logging.getLogger("whatif.face_masker")

_OCCLUDER_SESSION: onnxruntime.InferenceSession | None = None
_LOCK = threading.Lock()

# FaceFusion mask stack — computed on target crop before swap (not after).
MASK_TYPES: tuple[str, ...] = ("box", "occlusion")
MASK_BLUR = 0.3
MASK_PADDING: tuple[int, int, int, int] = (0, 0, 0, 0)  # top, right, bottom, left (%)

OCCLUDER_MODEL = "xseg_1.onnx"
OCCLUDER_SIZE = (256, 256)
OCCLUDER_URL = (
    "https://github.com/facefusion/facefusion-assets/releases/download/"
    "models-3.1.0/xseg_1.onnx"
)


def _providers() -> list[str]:
    available = onnxruntime.get_available_providers()
    if "CUDAExecutionProvider" in available:
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    if "CoreMLExecutionProvider" in available:
        return ["CoreMLExecutionProvider", "CPUExecutionProvider"]
    return ["CPUExecutionProvider"]


def _occluder_path() -> Path:
    return _engine_models_dir() / OCCLUDER_MODEL


def ensure_occluder() -> None:
    path = _occluder_path()
    if not path.is_file():
        raise ValueError(
            f"Occlusion model missing: {OCCLUDER_MODEL}. "
            f"Download to {_engine_models_dir()}: {OCCLUDER_URL}"
        )


def _get_occluder() -> onnxruntime.InferenceSession:
    global _OCCLUDER_SESSION
    with _LOCK:
        if _OCCLUDER_SESSION is None:
            path = _occluder_path()
            ensure_occluder()
            log.info("loading occlusion model: %s", path.name)
            _OCCLUDER_SESSION = onnxruntime.InferenceSession(
                str(path),
                providers=_providers(),
            )
        return _OCCLUDER_SESSION


def create_box_mask(
    crop_bgr: np.ndarray,
    blur: float = MASK_BLUR,
    padding: Sequence[int] = MASK_PADDING,
) -> np.ndarray:
    """Soft rectangular mask with edge feathering (FaceFusion box mask)."""
    crop_h, crop_w = crop_bgr.shape[:2]
    blur_amount = int(crop_w * 0.5 * blur)
    blur_area = max(blur_amount // 2, 1)
    mask = np.ones((crop_h, crop_w), dtype=np.float32)
    top, right, bottom, left = padding
    mask[: max(blur_area, int(crop_h * top / 100)), :] = 0
    mask[-max(blur_area, int(crop_h * bottom / 100)) :, :] = 0
    mask[:, : max(blur_area, int(crop_w * left / 100))] = 0
    mask[:, -max(blur_area, int(crop_w * right / 100)) :] = 0
    if blur_amount > 0:
        mask = cv2.GaussianBlur(mask, (0, 0), blur_amount * 0.25)
    return mask


def create_occlusion_mask(crop_bgr: np.ndarray) -> np.ndarray:
    """XSeg occlusion mask — keeps hair/glasses/hands out of swap region."""
    session = _get_occluder()
    resized = cv2.resize(crop_bgr, OCCLUDER_SIZE)
    frame = np.expand_dims(resized, axis=0).astype(np.float32) / 255.0
    frame = frame.transpose(0, 1, 2, 3)
    mask = session.run(None, {"input": frame})[0][0]
    if mask.ndim == 3:
        mask = mask[:, :, 0]
    mask = mask.clip(0, 1).astype(np.float32)
    mask = cv2.resize(mask, (crop_bgr.shape[1], crop_bgr.shape[0]))
    return (cv2.GaussianBlur(mask.clip(0, 1), (0, 0), 5).clip(0.5, 1) - 0.5) * 2


def build_crop_mask(crop_bgr: np.ndarray) -> np.ndarray:
    """Combine enabled mask types (minimum = tightest intersection)."""
    masks: list[np.ndarray] = []
    if "box" in MASK_TYPES:
        masks.append(create_box_mask(crop_bgr, MASK_BLUR, MASK_PADDING))
    if "occlusion" in MASK_TYPES:
        masks.append(create_occlusion_mask(crop_bgr))
    if not masks:
        h, w = crop_bgr.shape[:2]
        return np.ones((h, w), dtype=np.float32)
    return np.minimum.reduce(masks).clip(0, 1)
