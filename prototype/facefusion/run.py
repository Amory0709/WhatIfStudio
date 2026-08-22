#!/usr/bin/env python3
"""PROTOTYPE — FaceFusion vs booth eval. See QUESTION.md and README.md."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTO = Path(__file__).resolve().parent
CONFIG_PATH = PROTO / "config.json"
OUTPUTS = PROTO / "outputs"
MANIFEST_PATH = PROTO / "manifest.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_portraits() -> list[dict]:
    cfg = load_config()
    path = PROTO / cfg.get("portraits_file", "portraits-female.json")
    return json.loads(path.read_text(encoding="utf-8"))["portraits"]


def gallery_dir() -> Path:
    return ROOT / "apps" / "web" / "public" / "gallery"


def portrait_path(portrait_id: str) -> Path | None:
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = gallery_dir() / f"{portrait_id}{ext}"
        if p.is_file():
            return p
    return None


def default_upload() -> Path:
    cfg = load_config()
    rel = cfg.get("upload_default", ".scratch/diagnose/my-upload.jpg")
    p = ROOT / rel
    if p.is_file():
        return p
    return ROOT / "prototype" / "flux-identity" / "fixtures" / "prototype-upload.jpg"


def setup_api_env() -> None:
    os.environ.setdefault("WHATIF_ENGINE_DIR", str(ROOT / "apps" / "api" / "engine"))
    os.environ.setdefault("GALLERY_DIR", str(gallery_dir()))
    api = str(ROOT / "apps" / "api")
    if api not in sys.path:
        sys.path.insert(0, api)


def write_manifest(upload: Path, methods_run: list[str]) -> None:
    portraits = load_portraits()
    variants: list[dict] = []
    for item in portraits:
        pid = item["id"]
        src = portrait_path(pid)
        row: dict = {
            "portrait_id": pid,
            "portrait_tag": item.get("tag", ""),
            "label": item.get("label", pid),
            "portrait_source": src.relative_to(ROOT).as_posix() if src else None,
            "outputs": {},
        }
        for method in methods_run:
            for ext in (".png", ".jpg"):
                out = OUTPUTS / method / f"{pid}{ext}"
                if out.is_file():
                    row["outputs"][method] = out.relative_to(PROTO).as_posix()
                    break
        variants.append(row)

    manifest = {
        "prototype": "facefusion",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "upload": upload.relative_to(ROOT).as_posix() if upload.is_relative_to(ROOT) else str(upload),
        "methods": {k: v for k, v in load_config()["methods"].items() if k in methods_run},
        "variants": variants,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def cmd_check() -> int:
    setup_api_env()
    missing = [p["id"] for p in load_portraits() if portrait_path(p["id"]) is None]
    upload = default_upload()

    from ff_cli import is_available, resolve_home

    print("PROTOTYPE facefusion check")
    print(f"  upload: {upload} {'OK' if upload.is_file() else 'MISSING'}")
    print(f"  gallery missing: {len(missing)}")
    for mid in missing:
        print(f"    - {mid}")
    ff = resolve_home()
    print(f"  FaceFusion CLI: {'OK ' + str(ff) if ff else 'not installed (optional)'}")
    print(f"  ff_native: uses apps/api face_masker + inswapper")
    return 0 if upload.is_file() and not missing else 1


def run_hybrid(upload: Path) -> None:
    setup_api_env()
    from app.swap import _perform_hybrid_inswapper_swap

    out = OUTPUTS / "hybrid"
    out.mkdir(parents=True, exist_ok=True)
    face = upload.read_bytes()
    for item in load_portraits():
        pid = item["id"]
        src = portrait_path(pid)
        if src is None:
            continue
        print(f"  hybrid {pid}")
        (out / f"{pid}.png").write_bytes(
            _perform_hybrid_inswapper_swap(str(src), face)
        )


def run_booth(upload: Path) -> None:
    setup_api_env()
    from app.swap import perform_swap

    out = OUTPUTS / "booth"
    out.mkdir(parents=True, exist_ok=True)
    face = upload.read_bytes()
    for item in load_portraits():
        pid = item["id"]
        src = portrait_path(pid)
        if src is None:
            continue
        print(f"  booth {pid}")
        (out / f"{pid}.png").write_bytes(perform_swap(str(src), face, job_id="ff-proto"))


def run_native(upload: Path) -> None:
    from ff_native import perform_ff_native_swap

    out = OUTPUTS / "ff_native"
    out.mkdir(parents=True, exist_ok=True)
    face = upload.read_bytes()
    for item in load_portraits():
        pid = item["id"]
        src = portrait_path(pid)
        if src is None:
            continue
        print(f"  ff_native {pid}")
        (out / f"{pid}.png").write_bytes(perform_ff_native_swap(str(src), face))


def run_cli_method(upload: Path, method_key: str) -> None:
    from ff_cli import run_headless

    cfg = load_config()["methods"][method_key]
    out = OUTPUTS / method_key
    out.mkdir(parents=True, exist_ok=True)
    for item in load_portraits():
        pid = item["id"]
        src = portrait_path(pid)
        if src is None:
            continue
        dest = out / f"{pid}.jpg"
        print(f"  {method_key} {pid}")
        run_headless(
            upload,
            src,
            dest,
            processors=cfg["processors"],
            face_swapper_model=cfg["face_swapper_model"],
            face_mask_types=cfg["face_mask_types"],
            face_mask_blur=float(cfg.get("face_mask_blur", 0.3)),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="FaceFusion prototype eval")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="Verify upload, gallery, optional FaceFusion CLI")

    p_all = sub.add_parser("all", help="Run booth + ff_native + hybrid (+ CLI if installed)")
    p_all.add_argument("--upload", type=Path, default=None)

    for name in ("booth", "native", "hybrid"):
        p = sub.add_parser(name, help=f"Run {name} only")
        p.add_argument("--upload", type=Path, default=None)

    p_cli = sub.add_parser("cli", help="Run official FaceFusion CLI preset")
    p_cli.add_argument("preset", choices=["ff_cli_inswapper", "ff_cli_hyperswap"])
    p_cli.add_argument("--upload", type=Path, default=None)

    args = parser.parse_args()
    if args.cmd == "check":
        return cmd_check()

    upload = (args.upload or default_upload()).resolve()
    if not upload.is_file():
        print(f"Upload not found: {upload}", file=sys.stderr)
        return 2

    methods_run: list[str] = []

    if args.cmd in ("all", "booth"):
        print("Running booth baseline...")
        run_booth(upload)
        methods_run.append("booth")

    if args.cmd in ("all", "hybrid"):
        print("Running hybrid (FF mask + booth post)...")
        run_hybrid(upload)
        methods_run.append("hybrid")

    if args.cmd in ("all", "native"):
        print("Running ff_native (box + XSeg masks)...")
        run_native(upload)
        methods_run.append("ff_native")

    if args.cmd == "all":
        from ff_cli import is_available

        if is_available():
            for key in ("ff_cli_inswapper",):
                try:
                    print(f"Running {key}...")
                    run_cli_method(upload, key)
                    methods_run.append(key)
                except subprocess.CalledProcessError as exc:
                    print(f"  CLI failed: {exc}", file=sys.stderr)
        else:
            print("FaceFusion CLI not installed — skip (see setup.ps1)")

    if args.cmd == "cli":
        run_cli_method(upload, args.preset)
        methods_run.append(args.preset)

    write_manifest(upload, methods_run)
    print(f"\nOutputs -> {OUTPUTS}")
    print(f"Manifest -> {MANIFEST_PATH}")
    print("Open: npm run prototype:facefusion:serve  ->  http://127.0.0.1:8766/eval.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
