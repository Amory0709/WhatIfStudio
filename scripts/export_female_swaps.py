#!/usr/bin/env python3
"""Export swap PNGs for every female gallery portrait (genderage detection)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPLOAD = ROOT / ".scratch" / "diagnose" / "my-upload.jpg"
OUT = ROOT / ".scratch" / "diagnose" / "outputs" / "female-tuned"
LIST_SCRIPT = ROOT / "scripts" / "list_female_portraits.py"
GALLERY = ROOT / "apps" / "web" / "public" / "gallery"


def female_portrait_ids() -> list[str]:
    env = os.environ.copy()
    env.setdefault("WHATIF_ENGINE_DIR", str(ROOT / "apps" / "api" / "engine"))
    raw = subprocess.check_output(
        [sys.executable, str(LIST_SCRIPT)],
        env=env,
        text=True,
    )
    ids: list[str] = []
    for line in raw.splitlines():
        if "\t" not in line:
            continue
        gender, stem = line.split("\t", 1)
        if gender == "female":
            ids.append(stem.strip())
    return ids


def main() -> int:
    face_shape = "--face-shape" in sys.argv
    if face_shape:
        sys.argv.remove("--face-shape")

    if not UPLOAD.is_file():
        print(f"Missing upload: {UPLOAD}", file=sys.stderr)
        print("Take a selfie at http://127.0.0.1:8000/diagnose-selfie", file=sys.stderr)
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
    if face_shape:
        out_dir = OUT.parent / "female-face-shape"
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = OUT
    face_bytes = UPLOAD.read_bytes()
    ids = female_portrait_ids()
    if not ids:
        print("No female portraits detected in gallery.", file=sys.stderr)
        return 1

    print(f"Female portraits ({len(ids)}):", file=sys.stderr)
    for pid in ids:
        src = GALLERY / f"{pid}.jpg"
        if not src.is_file():
            for ext in (".jpeg", ".png", ".webp"):
                alt = GALLERY / f"{pid}{ext}"
                if alt.is_file():
                    src = alt
                    break
        if not src.is_file():
            print(f"  skip missing: {pid}", file=sys.stderr)
            continue
        dest = out_dir / f"{pid}.png"
        dest.write_bytes(
            perform_swap(
                str(src),
                face_bytes,
                job_id="female-export",
                transfer_face_shape=face_shape,
            )
        )
        print(f"  {dest}", file=sys.stderr)

    print(f"\nDone -> {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
