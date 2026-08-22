"""Helpers for booth face-swap quality (providers, crop, blend, sanity)."""
from __future__ import annotations

import os
from typing import Any, Tuple

import cv2
import numpy as np

# Full-body gallery shots: crop around face instead of swapping the whole frame.
CROP_MARGIN = 0.50
TARGET_FACE_FRAC_IN_CROP = 0.42
MAX_CROP_SCALE = 2.0

ENV_SHARPNESS = "WHATIF_SWAP_SHARPNESS"
ENV_POISSON = "WHATIF_POISSON_BLEND"
ENV_PRESERVE_EXPRESSION = "WHATIF_PRESERVE_EXPRESSION"
DEFAULT_SHARPNESS = 0.45
DEFAULT_EXPRESSION_STRENGTH = 0.82


def ensure_execution_providers() -> None:
    """API path never runs DLC CLI — providers stay [] without this."""
    from modules import globals as g
    import onnxruntime

    if g.execution_providers:
        return
    available = onnxruntime.get_available_providers()
    if "CUDAExecutionProvider" in available:
        g.execution_providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    elif "DmlExecutionProvider" in available:
        g.execution_providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
    elif "CoreMLExecutionProvider" in available:
        g.execution_providers = ["CoreMLExecutionProvider", "CPUExecutionProvider"]
    else:
        g.execution_providers = ["CPUExecutionProvider"]


def booth_sharpness() -> float:
    raw = os.environ.get(ENV_SHARPNESS, str(DEFAULT_SHARPNESS)).strip()
    try:
        return float(np.clip(float(raw), 0.0, 1.5))
    except ValueError:
        return DEFAULT_SHARPNESS


def booth_poisson_blend() -> bool:
    return os.environ.get(ENV_POISSON, "").strip().lower() in ("1", "true", "yes")


def face_width_frac(face: Any, img_w: int) -> float:
    return float(face.bbox[2] - face.bbox[0]) / max(img_w, 1)


def extract_face_crop(img: np.ndarray, face: Any) -> Tuple[Tuple[int, int, int, int], np.ndarray]:
    """Square crop around detected face — SLB full-body portraits need this."""
    h, w = img.shape[:2]
    x1, y1, x2, y2 = (float(v) for v in face.bbox)
    bw, bh = x2 - x1, y2 - y1
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    half = max(bw, bh) * (0.5 + CROP_MARGIN)
    rx1 = int(max(0, np.floor(cx - half)))
    ry1 = int(max(0, np.floor(cy - half)))
    rx2 = int(min(w, np.ceil(cx + half)))
    ry2 = int(min(h, np.ceil(cy + half)))
    if rx2 <= rx1 or ry2 <= ry1:
        return (0, 0, w, h), img.copy()
    return (rx1, ry1, rx2, ry2), img[ry1:ry2, rx1:rx2].copy()


def prepare_crop_for_swap(crop: np.ndarray, face: Any) -> Tuple[np.ndarray, float]:
    """Upscale crop only when face is tiny — less upscale/downscale = less blur."""
    cw = crop.shape[1]
    frac = face_width_frac(face, cw)
    if frac >= TARGET_FACE_FRAC_IN_CROP:
        return crop, 1.0
    scale = min(MAX_CROP_SCALE, TARGET_FACE_FRAC_IN_CROP / max(frac, 0.04))
    scale = max(1.2, scale)
    up = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
    return up, scale


def downscale_image(img: np.ndarray, scale: float) -> np.ndarray:
    if scale <= 1.0:
        return img
    h, w = img.shape[:2]
    return cv2.resize(
        img,
        (max(1, int(w / scale)), max(1, int(h / scale))),
        interpolation=cv2.INTER_LANCZOS4,
    )


def sharpen_crop(img: np.ndarray, strength: float | None = None) -> np.ndarray:
    """Unsharp mask — recovers detail lost to 128px InSwapper + resize."""
    amount = booth_sharpness() if strength is None else strength
    if amount <= 0:
        return img
    try:
        from modules.gpu_processing import gpu_sharpen

        return gpu_sharpen(img, strength=amount, sigma=1.2)
    except Exception:
        blur = cv2.GaussianBlur(img, (0, 0), 1.2)
        return cv2.addWeighted(img, 1.0 + amount, blur, -amount, 0)


def harmonize_face_color(swapped: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Light LAB match to portrait crop — natural default booth blend."""
    from modules.processors.frame.face_swapper import apply_color_transfer

    matched = apply_color_transfer(swapped, reference)
    return cv2.addWeighted(matched, 0.5, swapped, 0.5, 0)


def extract_source_face_patch(source_img: np.ndarray, face: Any) -> np.ndarray:
    """Square patch around the uploaded face — skin-tone reference for full-appearance mode."""
    h, w = source_img.shape[:2]
    x1, y1, x2, y2 = (float(v) for v in face.bbox)
    bw, bh = x2 - x1, y2 - y1
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    half = max(bw, bh) * 0.65
    rx1 = int(max(0, np.floor(cx - half)))
    ry1 = int(max(0, np.floor(cy - half)))
    rx2 = int(min(w, np.ceil(cx + half)))
    ry2 = int(min(h, np.ceil(cy + half)))
    if rx2 <= rx1 or ry2 <= ry1:
        return source_img.copy()
    return source_img[ry1:ry2, rx1:rx2].copy()


def apply_source_skin_tone(
    swapped: np.ndarray,
    source_patch: np.ndarray,
    strength: float = 0.82,
) -> np.ndarray:
    """Match swapped face color to the user's upload (not the portrait subject)."""
    from modules.processors.frame.face_swapper import apply_color_transfer

    if source_patch.size == 0 or swapped.size == 0:
        return swapped
    if source_patch.shape[0] != swapped.shape[0] or source_patch.shape[1] != swapped.shape[1]:
        source_patch = cv2.resize(
            source_patch,
            (swapped.shape[1], swapped.shape[0]),
            interpolation=cv2.INTER_AREA,
        )
    toned = apply_color_transfer(swapped, source_patch)
    strength = float(np.clip(strength, 0.0, 1.0))
    if strength >= 1.0:
        return toned
    return cv2.addWeighted(toned, strength, swapped, 1.0 - strength, 0)


def apply_full_head_from_source(swapped: np.ndarray, source_patch: np.ndarray) -> np.ndarray:
    """InSwapper enhanced — user's skin tone only (no pixel overlay)."""
    return apply_source_skin_tone(swapped, source_patch, strength=0.88)


def booth_expression_strength() -> float:
    raw = os.environ.get(ENV_PRESERVE_EXPRESSION, str(DEFAULT_EXPRESSION_STRENGTH)).strip()
    try:
        return float(np.clip(float(raw), 0.0, 1.0))
    except ValueError:
        return DEFAULT_EXPRESSION_STRENGTH


def preserve_portrait_expression(
    swapped: np.ndarray,
    reference: np.ndarray,
    face: Any,
    strength: float | None = None,
) -> np.ndarray:
    """Keep gallery smile / mouth from the portrait — stops creepy upload grins."""
    amount = booth_expression_strength() if strength is None else float(np.clip(strength, 0.0, 1.0))
    if amount <= 0 or face.kps is None:
        return swapped

    h, w = swapped.shape[:2]
    if reference.shape[:2] != (h, w):
        reference = cv2.resize(reference, (w, h), interpolation=cv2.INTER_AREA)

    kps = face.kps.astype(np.float32)
    nose_y = float(kps[2][1])
    mouth_y = float((kps[3][1] + kps[4][1]) / 2.0)
    split_y = int(nose_y + max(4.0, (mouth_y - nose_y) * 0.25))
    fade_h = max(10, int((mouth_y - split_y) * 1.8))

    mask = np.zeros((h, w), dtype=np.float32)
    for y in range(h):
        if y < split_y:
            m = 0.0
        elif y >= split_y + fade_h:
            m = amount
        else:
            t = (y - split_y) / fade_h
            m = amount * (t * t)
        mask[y, :] = m

    ml_x, mr_x = float(kps[3][0]), float(kps[4][0])
    pad = max(12.0, (mr_x - ml_x) * 0.45)
    x1 = int(max(0, np.floor(ml_x - pad)))
    x2 = int(min(w, np.ceil(mr_x + pad)))
    side_fade = max(6, int(pad * 0.35))
    for x in range(w):
        if x < x1:
            fade = max(0.0, 1.0 - (x1 - x) / side_fade)
            mask[:, x] *= fade
        elif x >= x2:
            fade = max(0.0, 1.0 - (x - x2 + 1) / side_fade)
            mask[:, x] *= fade

    k = max(3, (min(h, w) // 24) | 1)
    mask = cv2.GaussianBlur(mask, (k, k), k / 3)
    blended = swapped.astype(np.float32) * (1.0 - mask[..., None]) + reference.astype(np.float32) * mask[..., None]
    return np.clip(blended, 0, 255).astype(np.uint8)


def adaptive_soft_top_frac(crop: np.ndarray) -> float:
    """Top feather for paste_crop_back.

    Values above ~0.12 bleed the original portrait back on hair-heavy crops and
    hurt booth identity (see scripts/diagnose_swap_stages.py). Industrial
    portraits already landed at 0.12; only family-day hair shots hit 0.24.
    """
    _ = crop
    return 0.12


def _crop_feather_mask(h: int, w: int, margin_frac: float = 0.06) -> np.ndarray:
    mask = np.ones((h, w), dtype=np.float32)
    mh = max(1, int(h * margin_frac))
    mw = max(1, int(w * margin_frac))
    for i in range(mh):
        fade = (i + 1) / (mh + 1)
        mask[i, :] *= fade
        mask[h - 1 - i, :] *= fade
    for j in range(mw):
        fade = (j + 1) / (mw + 1)
        mask[:, j] *= fade
        mask[:, w - 1 - j] *= fade
    k = max(3, (min(h, w) // 20) | 1)
    return cv2.GaussianBlur(mask, (k, k), k / 4)


def paste_crop_back(
    canvas: np.ndarray,
    rect: Tuple[int, int, int, int],
    swapped: np.ndarray,
    original_crop: np.ndarray,
    *,
    soft_top_frac: float = 0.0,
) -> np.ndarray:
    """Paste swapped crop — sharp center, soft edge only."""
    x1, y1, x2, y2 = rect
    th, tw = y2 - y1, x2 - x1
    if th <= 0 or tw <= 0:
        return canvas
    if swapped.shape[0] != th or swapped.shape[1] != tw:
        interp = cv2.INTER_LANCZOS4 if swapped.shape[0] < th else cv2.INTER_AREA
        swapped = cv2.resize(swapped, (tw, th), interpolation=interp)
    edge = 0.06
    mask = _crop_feather_mask(th, tw, margin_frac=edge)
    if soft_top_frac > 0:
        top = max(1, int(th * soft_top_frac))
        for i in range(top):
            # Ease-in so hairline keeps more original portrait texture.
            t = (i + 1) / (top + 1)
            mask[i, :] *= t * t
    mask = mask[..., None]
    blended = swapped.astype(np.float32) * mask + original_crop.astype(np.float32) * (1.0 - mask)
    out = canvas.copy()
    out[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)
    return out


def swap_output_sane(img: np.ndarray, face: Any) -> bool:
    """Reject charcoal smear / failed ONNX paste."""
    x1, y1, x2, y2 = (int(v) for v in face.bbox)
    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return True
    roi = img[y1:y2, x1:x2]
    if roi.size == 0:
        return True
    mean = float(roi.mean())
    std = float(roi.std())
    if mean < 55 and std > 35:
        return False
    if mean < 35:
        return False
    return True
