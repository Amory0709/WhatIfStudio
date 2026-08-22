"""Swap model registry — ids, metadata, and availability checks."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SwapModelId = Literal[
    "inswapper_128",
    "reswapper_256",
    "hififace_256",
    "hyperswap_256",
]

DEFAULT_SWAP_MODEL: SwapModelId = "inswapper_128"
FACE_SHAPE_MODEL: SwapModelId = "hififace_256"

# Env override for server default (UI can still pick per-request).
ENV_SWAP_MODEL = "WHATIF_SWAP_MODEL"


@dataclass(frozen=True)
class SwapModelSpec:
    id: SwapModelId
    label: str
    description: str
    likeness: str  # low | medium | high | highest
    backend: str  # dlc | facefusion
    model_files: tuple[str, ...]
    download_urls: tuple[str, ...]
    experimental: bool = False
    transfers_face_shape: bool = False


def _engine_models_dir() -> Path:
    """Resolve .../engine/models (same layout as swap.py / face_analyser)."""
    env = os.environ.get("WHATIF_ENGINE_DIR", "").strip()
    if env:
        return Path(env).resolve() / "models"
    # Dev fallback when env unset: apps/api/engine/models next to this package.
    app_dir = Path(__file__).resolve().parents[1]
    candidate = app_dir / "engine" / "models"
    if candidate.is_dir():
        return candidate
    return Path(".").resolve() / "models"


MODELS: dict[SwapModelId, SwapModelSpec] = {
    "inswapper_128": SwapModelSpec(
        id="inswapper_128",
        label="InSwapper 128 (FaceFusion)",
        description="FaceFusion warp/blend + InSwapper — natural booth default.",
        likeness="medium",
        backend="facefusion",
        model_files=("inswapper_128.onnx", "inswapper_128_fp16.onnx"),
        download_urls=(
            "https://huggingface.co/hacksider/deep-live-cam/resolve/main/inswapper_128.onnx",
        ),
    ),
    "reswapper_256": SwapModelSpec(
        id="reswapper_256",
        label="ReSwapper 256",
        description="Higher-res InSwapper. Sharper detail, same natural blend as default.",
        likeness="medium",
        backend="dlc",
        model_files=("reswapper_256.onnx",),
        download_urls=(
            "https://huggingface.co/somanchiu/reswapper/resolve/main/"
            "reswapper_256-1567500_originalInswapperClassCompatible.onnx",
        ),
    ),
    "hififace_256": SwapModelSpec(
        id="hififace_256",
        label="HifiFace 256 (my head only)",
        description="Your expression, skin, features, and face shape. Target image keeps outfit and background only.",
        likeness="high",
        backend="facefusion",
        model_files=("hififace_unofficial_256.onnx", "crossface_hififace.onnx"),
        download_urls=(
            "https://github.com/facefusion/facefusion-assets/releases/download/"
            "models-3.1.0/hififace_unofficial_256.onnx",
            "https://github.com/facefusion/facefusion-assets/releases/download/"
            "models-3.4.0/crossface_hififace.onnx",
        ),
        transfers_face_shape=True,
    ),
    "hyperswap_256": SwapModelSpec(
        id="hyperswap_256",
        label="HyperSwap 256 (strong likeness)",
        description="Max identity transfer — experimental; may look uncanny on booth portraits.",
        likeness="high",
        backend="facefusion",
        model_files=("hyperswap_1c_256.onnx",),
        download_urls=(
            "https://github.com/facefusion/facefusion-assets/releases/download/"
            "models-3.3.0/hyperswap_1c_256.onnx",
        ),
        experimental=True,
    ),
}


def normalize_model_id(raw: str | None) -> SwapModelId:
    if not raw:
        return resolve_default_model()
    key = raw.strip().lower().replace("-", "_")
    aliases = {
        "inswapper": "inswapper_128",
        "inswapper128": "inswapper_128",
        "reswapper": "reswapper_256",
        "reswapper256": "reswapper_256",
        "hififace": "hififace_256",
        "hyperswap": "hyperswap_256",
        "hyperswap_1c_256": "hyperswap_256",
        "hyperswap_1c": "hyperswap_256",
    }
    key = aliases.get(key, key)  # type: ignore[assignment]
    if key not in MODELS:
        known = ", ".join(MODELS)
        raise ValueError(f"Unknown swap model '{raw}'. Choose one of: {known}")
    return key  # type: ignore[return-value]


def resolve_default_model() -> SwapModelId:
    env = os.environ.get(ENV_SWAP_MODEL, "").strip()
    if env:
        return normalize_model_id(env)
    return DEFAULT_SWAP_MODEL


def _experimental_enabled() -> bool:
    return os.environ.get("WHATIF_EXPERIMENTAL_SWAP", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def resolve_model_for_request(
    raw: str | None,
    *,
    transfer_face_shape: bool = False,
) -> SwapModelId:
    """Pick swap model; face-shape mode forces HifiFace when weights exist."""
    if transfer_face_shape:
        if not model_is_available(FACE_SHAPE_MODEL):
            raise ValueError(
                "Face-shape swap needs HifiFace weights. From repo root run: "
                "python scripts/download_swap_models.py hififace_256"
            )
        return FACE_SHAPE_MODEL

    model_id = normalize_model_id(raw or resolve_default_model())
    spec = MODELS[model_id]
    if spec.experimental and not _experimental_enabled():
        return DEFAULT_SWAP_MODEL
    return model_id


def model_is_available(model_id: SwapModelId) -> bool:
    spec = MODELS[model_id]
    models_dir = _engine_models_dir()
    if model_id == "inswapper_128":
        return any((models_dir / f).is_file() for f in spec.model_files)
    if model_id == "reswapper_256":
        return (models_dir / "reswapper_256.onnx").is_file()
    return all((models_dir / f).is_file() for f in spec.model_files)


def list_models() -> list[dict]:
    show_experimental = _experimental_enabled()
    out: list[dict] = []
    for spec in MODELS.values():
        if spec.experimental and not show_experimental:
            continue
        out.append(
            {
                "id": spec.id,
                "label": spec.label,
                "description": spec.description,
                "likeness": spec.likeness,
                "available": model_is_available(spec.id),
                "download_urls": list(spec.download_urls),
                "experimental": spec.experimental,
                "transfers_face_shape": spec.transfers_face_shape,
            }
        )
    return out


def face_shape_model_available() -> bool:
    return model_is_available(FACE_SHAPE_MODEL)


def reswapper_path() -> Path:
    return _engine_models_dir() / "reswapper_256.onnx"
