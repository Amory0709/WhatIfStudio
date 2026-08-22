#!/usr/bin/env python3
"""Export swap PNGs for the diagnose selfie — visual check after pipeline tweaks."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPLOAD = ROOT / ".scratch" / "diagnose" / "my-upload.jpg"
GALLERY = ROOT / "apps" / "web" / "public" / "gallery"
OUT = ROOT / ".scratch" / "diagnose" / "outputs"

DEFAULT_IDS = [
    "tier-2-people-lab-NEPEC-sugar-land-NAL-7R55891",
    "tier-1-operating-base-coca-amr-4904",
    "tier-2-people-drilling-offshore-operations-el-nido-asa-3917-4inch",
]


def main() -> int:
    if not UPLOAD.is_file():
        print(f"Missing upload: {UPLOAD}", file=sys.stderr)
        return 2

    os.environ.setdefault("WHATIF_ENGINE_DIR", str(ROOT / "apps" / "api" / "engine"))
    os.environ.setdefault("GALLERY_DIR", str(GALLERY))
    api = str(ROOT / "apps" / "api")
    if api not in sys.path:
        sys.path.insert(0, api)
    eng = os.environ["WHATIF_ENGINE_DIR"]
    if eng not in sys.path:
        sys.path.insert(0, eng)

    from app.swap import perform_swap

    OUT.mkdir(parents=True, exist_ok=True)
    face_bytes = UPLOAD.read_bytes()
    ids = sys.argv[1:] or DEFAULT_IDS

    for pid in ids:
        src = GALLERY / f"{pid}.jpg"
        if not src.is_file():
            print(f"skip missing: {src}", file=sys.stderr)
            continue
        dest = OUT / f"{pid}.png"
        dest.write_bytes(perform_swap(str(src), face_bytes, job_id="diagnose-export"))
        print(dest)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
