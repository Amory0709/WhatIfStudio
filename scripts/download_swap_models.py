#!/usr/bin/env python3
"""Download optional face-swap model weights into apps/api/engine/models/."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
os.environ.setdefault("WHATIF_ENGINE_DIR", str(ROOT / "apps" / "api" / "engine"))

from app.swap_models import MODELS, normalize_model_id  # noqa: E402
from app.face_masker import OCCLUDER_MODEL, OCCLUDER_URL  # noqa: E402

MIN_ONNX_BYTES = 1_000_000  # reject HTML / LFS pointer stubs
MIN_SMALL_BYTES = 10_000  # embedding converters (crossface_*.onnx)

# Partial downloads must not pass validation.
FILE_MIN_BYTES: dict[str, int] = {
    "hififace_unofficial_256.onnx": 100_000_000,
    "hyperswap_1c_256.onnx": 300_000_000,
    "reswapper_256.onnx": 400_000_000,
    "inswapper_128.onnx": 200_000_000,
    "xseg_1.onnx": 50_000_000,
}


def _min_size(dest: Path) -> int:
    if dest.name in FILE_MIN_BYTES:
        return FILE_MIN_BYTES[dest.name]
    if dest.name.startswith("crossface_"):
        return MIN_SMALL_BYTES
    return MIN_ONNX_BYTES


def _curl_available() -> bool:
    return shutil.which("curl") is not None


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size >= _min_size(dest):
        print(f"skip  {dest.name} ({dest.stat().st_size // (1024 * 1024)} MB)")
        return

    if dest.is_file():
        dest.unlink()

    print(f"fetch {dest.name} …")
    if _curl_available():
        cmd = [
            "curl",
            "-L",
            "--fail",
            "-C",
            "-",
            "--retry",
            "10",
            "--retry-delay",
            "5",
            "--retry-all-errors",
            "-o",
            str(dest),
            url,
        ]
        if sys.platform == "win32":
            cmd.insert(1, "--ssl-no-revoke")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"curl failed for {dest.name}: {proc.stderr.strip()}")
    else:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "WhatIfStudio/1.0"},
        )
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = resp.read()
        dest.write_bytes(data)

    size = dest.stat().st_size
    min_sz = _min_size(dest)
    if size < min_sz:
        dest.unlink(missing_ok=True)
        raise RuntimeError(
            f"{dest.name} too small ({size} bytes) — download likely blocked. "
            "Try browser/VPN or: huggingface-cli download ..."
        )
    print(f"saved {dest} ({size // (1024 * 1024)} MB)")


def main(argv: list[str]) -> int:
    ids = [normalize_model_id(a) for a in argv] if argv else list(MODELS.keys())
    models_dir = Path(os.environ["WHATIF_ENGINE_DIR"]) / "models"

    for model_id in ids:
        spec = MODELS[model_id]
        print(f"\n=== {model_id} ===")
        for fname, url in zip(spec.model_files, spec.download_urls):
            dest = models_dir / fname
            if model_id == "reswapper_256":
                dest = models_dir / "reswapper_256.onnx"
            download(url, dest)
        if spec.backend == "facefusion":
            download(OCCLUDER_URL, models_dir / OCCLUDER_MODEL)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
