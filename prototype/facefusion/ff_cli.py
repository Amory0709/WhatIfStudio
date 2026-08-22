"""PROTOTYPE — invoke official FaceFusion headless-run when installed."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTO = Path(__file__).resolve().parent
VENDOR = PROTO / "vendor" / "facefusion"
ENGINE_MODELS = ROOT / "apps" / "api" / "engine" / "models"


def resolve_home() -> Path | None:
    raw = os.environ.get("FACEFUSION_HOME", "").strip()
    if raw:
        p = Path(raw).expanduser().resolve()
        return p if (p / "facefusion.py").is_file() else None
    if (VENDOR / "facefusion.py").is_file():
        return VENDOR
    return None


def is_available() -> bool:
    return resolve_home() is not None


def run_headless(
    upload: Path,
    portrait: Path,
    output: Path,
    *,
    processors: list[str],
    face_swapper_model: str,
    face_mask_types: list[str],
    face_mask_blur: float,
) -> None:
    home = resolve_home()
    if home is None:
        raise FileNotFoundError(
            "FaceFusion not found. Run: powershell -File prototype/facefusion/setup.ps1"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if ENGINE_MODELS.is_dir():
        env.setdefault("FACEFUSION_HOME", str(home))
        # FaceFusion stores models under .assets/models — symlink optional in setup.ps1

    mask_types = " ".join(face_mask_types)
    proc = " ".join(processors)
    cmd = [
        sys.executable,
        str(home / "facefusion.py"),
        "headless-run",
        "--source-paths",
        str(upload),
        "--target-path",
        str(portrait),
        "--output-path",
        str(output),
        "--processors",
        *processors,
        "--face-swapper-model",
        face_swapper_model,
        "--face-mask-types",
        *face_mask_types,
        "--face-mask-blur",
        str(face_mask_blur),
        "--execution-providers",
        "cpu",
    ]

    print("  $", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(home), env=env, check=True)
