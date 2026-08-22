"""Minimal face warp / paste helpers (adapted from FaceFusion face_helper)."""
from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np

WARP_TEMPLATES = {
    "arcface_128": np.array(
        [
            [0.36167656, 0.40387734],
            [0.63696719, 0.40235469],
            [0.50019687, 0.56044219],
            [0.38710391, 0.72160547],
            [0.61507734, 0.72034453],
        ],
        dtype=np.float32,
    ),
    "mtcnn_512": np.array(
        [
            [0.36562865, 0.46733799],
            [0.63305391, 0.46585885],
            [0.50019127, 0.61942959],
            [0.39032951, 0.77598822],
            [0.61178945, 0.77476328],
        ],
        dtype=np.float32,
    ),
}


def estimate_affine(
    face_landmark_5: np.ndarray, template: str, crop_size: Tuple[int, int]
) -> np.ndarray:
    norm = WARP_TEMPLATES[template] * np.array([crop_size[0], crop_size[1]], dtype=np.float32)
    matrix, _ = cv2.estimateAffinePartial2D(
        face_landmark_5.astype(np.float32),
        norm,
        method=cv2.RANSAC,
        ransacReprojThreshold=100,
    )
    if matrix is None:
        raise ValueError("Failed to estimate face alignment affine matrix")
    return matrix


def warp_face(
    frame: np.ndarray,
    face_landmark_5: np.ndarray,
    template: str,
    crop_size: Tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    matrix = estimate_affine(face_landmark_5, template, crop_size)
    crop = cv2.warpAffine(
        frame,
        matrix,
        crop_size,
        borderMode=cv2.BORDER_REPLICATE,
        flags=cv2.INTER_AREA,
    )
    return crop, matrix


def elliptical_mask(size: Tuple[int, int], *, booth: bool = False) -> np.ndarray:
    h, w = size
    mask = np.zeros((h, w), dtype=np.float32)
    if booth:
        # Slightly lower ellipse — keep hard-hat / hairline from portrait, swap mid-face down.
        cy = h // 2 + int(h * 0.05)
        axes = (int(w * 0.40), int(h * 0.38))
        cv2.ellipse(mask, (w // 2, cy), axes, 0, 0, 360, 1, -1)
        top = max(1, int(h * 0.14))
        for i in range(top):
            mask[i, :] *= (i + 1) / (top + 1)
    else:
        cv2.ellipse(mask, (w // 2, h // 2), (int(w * 0.44), int(h * 0.44)), 0, 0, 360, 1, -1)
        top = max(1, int(h * 0.16))
        for i in range(top):
            t = (i + 1) / (top + 1)
            mask[i, :] *= t * t
    k = max(3, (min(h, w) // 20) | 1)
    return cv2.GaussianBlur(mask, (k | 1, k | 1), k / 3)


def paste_back(
    frame: np.ndarray,
    crop: np.ndarray,
    crop_mask: np.ndarray,
    affine_matrix: np.ndarray,
) -> np.ndarray:
    temp_h, temp_w = frame.shape[:2]
    crop_h, crop_w = crop.shape[:2]
    inv = cv2.invertAffineTransform(affine_matrix)
    corners = np.array(
        [[0, 0], [crop_w, 0], [crop_w, crop_h], [0, crop_h]], dtype=np.float32
    )
    pts = cv2.transform(corners.reshape(1, -1, 2), inv).reshape(-1, 2)
    x1 = int(max(0, np.floor(pts[:, 0].min())))
    y1 = int(max(0, np.floor(pts[:, 1].min())))
    x2 = int(min(temp_w, np.ceil(pts[:, 0].max())))
    y2 = int(min(temp_h, np.ceil(pts[:, 1].max())))
    paste_w, paste_h = x2 - x1, y2 - y1
    if paste_w <= 0 or paste_h <= 0:
        return frame

    paste_matrix = inv.copy()
    paste_matrix[0, 2] -= x1
    paste_matrix[1, 2] -= y1

    inv_mask = cv2.warpAffine(crop_mask, paste_matrix, (paste_w, paste_h)).clip(0, 1)
    inv_mask = inv_mask[..., None]
    inv_crop = cv2.warpAffine(
        crop, paste_matrix, (paste_w, paste_h), borderMode=cv2.BORDER_REPLICATE
    )

    out = frame.copy()
    region = out[y1:y2, x1:x2]
    blended = region * (1 - inv_mask) + inv_crop * inv_mask
    out[y1:y2, x1:x2] = blended.astype(frame.dtype)
    return out
