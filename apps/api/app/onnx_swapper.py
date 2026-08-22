"""FaceFusion pipeline for all swap models (InSwapper, HifiFace, HyperSwap)."""
from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Literal

import cv2
import numpy as np
import onnx
import onnxruntime
from onnx.numpy_helper import to_array

from .swap_models import MODELS, SwapModelId, _engine_models_dir
from .warp_helper import elliptical_mask, paste_back, warp_face

log = logging.getLogger("whatif.onnx_swapper")

# Booth: identity from upload, expression/smile from gallery portrait.
ENV_SOURCE_WEIGHT = "WHATIF_SWAP_SOURCE_WEIGHT"
DEFAULT_SOURCE_WEIGHT = 0.76
BOOTH_SOURCE_WEIGHT = "0.76"

ModelType = Literal["inswapper", "hyperswap", "hififace"]
MaskMode = Literal["ellipse", "facefusion"]

_SESSIONS: dict[str, onnxruntime.InferenceSession] = {}
_LOCK = threading.Lock()


@dataclass(frozen=True)
class _SwapConfig:
    template: str
    crop_size: tuple[int, int]
    model_type: ModelType
    mean: tuple[float, float, float]
    std: tuple[float, float, float]


def _providers() -> list[str]:
    available = onnxruntime.get_available_providers()
    if "CUDAExecutionProvider" in available:
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    if "CoreMLExecutionProvider" in available:
        return ["CoreMLExecutionProvider", "CPUExecutionProvider"]
    return ["CPUExecutionProvider"]


def _load_session(path: Path) -> onnxruntime.InferenceSession:
    key = str(path.resolve())
    with _LOCK:
        if key not in _SESSIONS:
            log.info("loading ONNX model: %s", path.name)
            _SESSIONS[key] = onnxruntime.InferenceSession(
                str(path),
                providers=_providers(),
            )
        return _SESSIONS[key]


@lru_cache(maxsize=8)
def _model_initializer(model_path: str) -> np.ndarray:
    """InSwapper latent matrix — last ONNX initializer (FaceFusion model_helper)."""
    graph = onnx.load(model_path).graph
    return to_array(graph.initializer[-1])


def _swap_config(model_id: SwapModelId) -> _SwapConfig:
    if model_id == "inswapper_128":
        return _SwapConfig("arcface_128", (128, 128), "inswapper", (0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
    if model_id == "reswapper_256":
        return _SwapConfig("arcface_128", (256, 256), "inswapper", (0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
    if model_id == "hififace_256":
        return _SwapConfig("mtcnn_512", (256, 256), "hififace", (0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
    if model_id == "hyperswap_256":
        return _SwapConfig("arcface_128", (256, 256), "hyperswap", (0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
    raise ValueError(f"Unknown swap model: {model_id}")


def _resolve_onnx_path(model_id: SwapModelId) -> Path:
    models_dir = _engine_models_dir()
    if model_id == "inswapper_128":
        for name in ("inswapper_128.onnx", "inswapper_128_fp16.onnx"):
            path = models_dir / name
            if path.is_file():
                return path
        raise FileNotFoundError("inswapper_128.onnx")
    if model_id == "reswapper_256":
        path = models_dir / "reswapper_256.onnx"
        if path.is_file():
            return path
        raise FileNotFoundError("reswapper_256.onnx")
    spec = MODELS[model_id]
    path = models_dir / spec.model_files[0]
    if not path.is_file():
        raise FileNotFoundError(spec.model_files[0])
    return path


def _prepare_crop(crop_bgr: np.ndarray, cfg: _SwapConfig) -> np.ndarray:
    mean = np.array(cfg.mean, dtype=np.float32)
    std = np.array(cfg.std, dtype=np.float32)
    rgb = crop_bgr[:, :, ::-1].astype(np.float32) / 255.0
    rgb = (rgb - mean) / std
    chw = rgb.transpose(2, 0, 1)
    return np.expand_dims(chw, axis=0).astype(np.float32)


def _normalize_output(out: np.ndarray, cfg: _SwapConfig) -> np.ndarray:
    chw = out[0].transpose(1, 2, 0)
    if cfg.model_type in ("hififace", "hyperswap"):
        std = np.array(cfg.std, dtype=np.float32)
        mean = np.array(cfg.mean, dtype=np.float32)
        chw = chw * std + mean
    rgb = np.clip(chw, 0, 1)
    return (rgb[:, :, ::-1] * 255).astype(np.uint8)


def _convert_embedding_hififace(embedding: np.ndarray) -> np.ndarray:
    path = _engine_models_dir() / "crossface_hififace.onnx"
    session = _load_session(path)
    out = session.run(None, {"input": embedding.reshape(1, -1).astype(np.float32)})[0]
    out = out.ravel()
    return (out / np.linalg.norm(out)).reshape(1, -1).astype(np.float32)


def _source_weight() -> float:
    raw = os.environ.get(ENV_SOURCE_WEIGHT, str(DEFAULT_SOURCE_WEIGHT)).strip()
    try:
        return float(np.clip(float(raw), 0.0, 1.0))
    except ValueError:
        return DEFAULT_SOURCE_WEIGHT


def _balance_embedding(source_emb: np.ndarray, target_emb: np.ndarray) -> np.ndarray:
    weight = _source_weight()
    if weight >= 1.0:
        out = source_emb.reshape(1, -1).astype(np.float32)
    elif weight <= 0.0:
        out = target_emb.reshape(1, -1).astype(np.float32)
    else:
        blend = float(np.interp(weight, [0.0, 1.0], [0.35, -0.35]))
        tgt = target_emb / np.linalg.norm(target_emb)
        src = source_emb.reshape(1, -1)
        tgt = tgt.reshape(1, -1)
        out = (src * (1 - blend) + tgt * blend).astype(np.float32)
    norm = np.linalg.norm(out)
    if norm > 0:
        out = out / norm
    return out.astype(np.float32)


def _prepare_source_embedding(
    model_id: SwapModelId,
    source_face: Any,
    target_face: Any,
    swapper_path: Path,
    cfg: _SwapConfig,
) -> np.ndarray:
    if cfg.model_type == "inswapper":
        init = _model_initializer(str(swapper_path))
        emb = source_face.embedding.reshape(1, -1).astype(np.float32)
        emb = np.dot(emb, init)
        emb = emb / np.linalg.norm(emb)
    elif cfg.model_type == "hyperswap":
        emb = source_face.normed_embedding.reshape(1, -1).astype(np.float32)
    else:
        raw = source_face.embedding.reshape(-1, 512).astype(np.float32)
        emb = _convert_embedding_hififace(raw)
    return _balance_embedding(emb, target_face.normed_embedding)


def swap_image(
    model_id: SwapModelId,
    source_bgr: np.ndarray,
    target_bgr: np.ndarray,
    source_face: Any,
    target_face: Any,
    *,
    full_appearance: bool = False,
    mask_mode: MaskMode = "ellipse",
) -> np.ndarray:
    cfg = _swap_config(model_id)
    swapper_path = _resolve_onnx_path(model_id)

    if source_face.kps is None or target_face.kps is None:
        raise ValueError("Face landmarks missing — detection failed")

    session = _load_session(swapper_path)
    crop, matrix = warp_face(target_bgr, target_face.kps, cfg.template, cfg.crop_size)
    if mask_mode == "facefusion":
        from .face_masker import build_crop_mask, ensure_occluder

        ensure_occluder()
        crop_mask = build_crop_mask(crop)
    else:
        crop_mask = elliptical_mask(cfg.crop_size, booth=full_appearance)
    source_emb = _prepare_source_embedding(model_id, source_face, target_face, swapper_path, cfg)
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


def ensure_models(model_id: SwapModelId) -> None:
    models_dir = _engine_models_dir()
    spec = MODELS[model_id]
    missing: list[str] = []
    try:
        _resolve_onnx_path(model_id)
    except FileNotFoundError as exc:
        missing.append(f"{exc} ← see {spec.download_urls}")
    if model_id == "hififace_256":
        cross = models_dir / "crossface_hififace.onnx"
        if not cross.is_file():
            missing.append(f"crossface_hififace.onnx ← {spec.download_urls[1]}")
    if missing:
        raise ValueError("Missing model weights:\n" + "\n".join(missing))
