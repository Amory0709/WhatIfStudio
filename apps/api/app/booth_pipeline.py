"""Booth pipeline metadata — tuned InSwapper path from prototype eval."""
from __future__ import annotations

import os

from .onnx_swapper import BOOTH_SOURCE_WEIGHT, ENV_SOURCE_WEIGHT
from .swap_helpers import booth_expression_strength, booth_sharpness
from .swap_models import DEFAULT_SWAP_MODEL

PIPELINE_ID = "facefusion+inswapper"


def booth_settings() -> dict[str, float | str]:
    raw = os.environ.get(ENV_SOURCE_WEIGHT, BOOTH_SOURCE_WEIGHT).strip()
    try:
        source_weight = float(raw)
    except ValueError:
        source_weight = float(BOOTH_SOURCE_WEIGHT)
    return {
        "pipeline": PIPELINE_ID,
        "default_model": DEFAULT_SWAP_MODEL,
        "source_weight": source_weight,
        "preserve_expression": booth_expression_strength(),
        "sharpness": booth_sharpness(),
    }
