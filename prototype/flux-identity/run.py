#!/usr/bin/env python3
"""PROTOTYPE — Flux identity eval harness. See QUESTION.md and README.md."""
from __future__ import annotations

import argparse
import json
import os
import shutil
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


def gallery_dir() -> Path:
    return ROOT / "apps" / "web" / "public" / "gallery"


def portrait_path(portrait_id: str) -> Path | None:
    base = gallery_dir()
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        candidate = base / f"{portrait_id}{ext}"
        if candidate.is_file():
            return candidate
    return None


def setup_api_env() -> None:
    os.environ.setdefault("WHATIF_ENGINE_DIR", str(ROOT / "apps" / "api" / "engine"))
    os.environ.setdefault("GALLERY_DIR", str(gallery_dir()))
    api_root = str(ROOT / "apps" / "api")
    if api_root not in sys.path:
        sys.path.insert(0, api_root)


def run_baseline(upload: Path) -> None:
    if not upload.is_file():
        raise SystemExit(f"Upload not found: {upload}")

    cfg = load_config()
    missing = [p["id"] for p in cfg["portraits"] if portrait_path(p["id"]) is None]
    if missing:
        raise SystemExit(
            "Gallery portraits missing under apps/web/public/gallery:\n"
            + "\n".join(f"  - {mid}" for mid in missing)
        )

    setup_api_env()
    from app.swap import perform_swap  # noqa: WPS433

    out_dir = OUTPUTS / "baseline_inswapper"
    out_dir.mkdir(parents=True, exist_ok=True)
    face_bytes = upload.read_bytes()

    print(f"Running InSwapper baseline ({len(cfg['portraits'])} portraits)...")
    for item in cfg["portraits"]:
        pid = item["id"]
        src = portrait_path(pid)
        assert src is not None
        dest = out_dir / f"{pid}.png"
        print(f"  - {pid}")
        png = perform_swap(str(src), face_bytes, job_id="prototype-baseline")
        dest.write_bytes(png)

    write_manifest(upload)
    print(f"\nBaseline done -> {out_dir}")
    print(f"Manifest -> {MANIFEST_PATH}")
    print("Next: generate PuLID / InstantID in ComfyUI (see workflows/README.md),")
    print("      import with: python run.py import --method pulid_inpaint --dir <folder>")
    print("Open eval: double-click eval.html and load manifest.json")


def import_outputs(method: str, source_dir: Path, strength: float | None) -> None:
    cfg = load_config()
    if method not in cfg["methods"]:
        raise SystemExit(f"Unknown method '{method}'. Choose: {', '.join(cfg['methods'])}")

    if not source_dir.is_dir():
        raise SystemExit(f"Not a directory: {source_dir}")

    dest_root = OUTPUTS / method
    dest_root.mkdir(parents=True, exist_ok=True)
    copied = 0

    for item in cfg["portraits"]:
        pid = item["id"]
        matches = sorted(source_dir.glob(f"{pid}*"))
        if not matches:
            for ext in (".png", ".jpg", ".jpeg", ".webp"):
                alt = source_dir / f"{pid}{ext}"
                if alt.is_file():
                    matches = [alt]
                    break
        if not matches:
            print(f"  skip (no file): {pid}")
            continue
        src = matches[0]
        if strength is not None:
            dest = dest_root / f"{pid}_strength_{strength:.2f}.png"
        else:
            dest = dest_root / f"{pid}.png"
        shutil.copy2(src, dest)
        copied += 1
        print(f"  - {src.name} -> {dest.relative_to(PROTO)}")

    if copied == 0:
        raise SystemExit(f"No files imported from {source_dir}")
    print(f"Imported {copied} file(s) into {dest_root.relative_to(PROTO)}")


def write_manifest(upload: Path | None) -> None:
    cfg = load_config()
    variants: list[dict] = []

    for method_id, spec in cfg["methods"].items():
        method_dir = OUTPUTS / method_id
        if not method_dir.is_dir():
            continue
        for item in cfg["portraits"]:
            pid = item["id"]
            portrait = portrait_path(pid)
            if method_id == "baseline_inswapper":
                candidates = [method_dir / f"{pid}.png"]
                strength = None
            else:
                candidates = sorted(method_dir.glob(f"{pid}_strength_*.png"))
                if not candidates:
                    candidates = [method_dir / f"{pid}.png"]
                strength = None
                if candidates and "_strength_" in candidates[0].name:
                    try:
                        strength = float(candidates[0].stem.split("_strength_")[-1])
                    except ValueError:
                        strength = None

            for path in candidates:
                if not path.is_file():
                    continue
                rel = path.relative_to(PROTO).as_posix()
                variants.append(
                    {
                        "id": f"{method_id}::{pid}::{path.stem}",
                        "method": method_id,
                        "method_label": spec["label"],
                        "portrait_id": pid,
                        "portrait_tag": item["tag"],
                        "strength": strength,
                        "image": rel,
                        "portrait_source": (
                            portrait.relative_to(ROOT).as_posix() if portrait else None
                        ),
                    }
                )

    manifest = {
        "prototype": "flux-identity",
        "question": (PROTO / "QUESTION.md").read_text(encoding="utf-8").strip(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "upload": str(upload.resolve()) if upload and upload.is_file() else None,
        "eval_gate": cfg["eval_gate"],
        "axes": ["identity", "scene_fidelity", "naturalness"],
        "variants": variants,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def cmd_check() -> None:
    cfg = load_config()
    print("Gallery portraits:")
    ok = True
    for item in cfg["portraits"]:
        path = portrait_path(item["id"])
        status = path.name if path else "MISSING"
        if not path:
            ok = False
        print(f"  [{item['tag']}] {item['id']} -> {status}")

    print("\nOutput folders:")
    for method_id in cfg["methods"]:
        method_dir = OUTPUTS / method_id
        count = len(list(method_dir.glob("*"))) if method_dir.is_dir() else 0
        print(f"  {method_id}: {count} file(s)")

    comfy = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
    print(f"\nComfyUI (optional): {comfy}")
    try:
        import urllib.request

        urllib.request.urlopen(f"{comfy.rstrip('/')}/system_stats", timeout=2)
        print("  status: reachable")
    except Exception as exc:
        print(f"  status: not reachable ({exc})")

    if not ok:
        raise SystemExit(1)


def cmd_comfy(method: str, upload: Path, comfy_url: str) -> None:
    from comfy_client import queue_workflow  # noqa: WPS433

    cfg = load_config()
    spec = cfg["methods"].get(method)
    if not spec or not spec.get("comfy_workflow"):
        raise SystemExit(f"Method '{method}' has no comfy_workflow in config.json")

    workflow_path = PROTO / spec["comfy_workflow"]
    if not workflow_path.is_file():
        raise SystemExit(
            f"Workflow missing: {workflow_path}\n"
            "Export API-format workflow from ComfyUI — see workflows/README.md"
        )

    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    strengths = cfg["inpaint_strengths"]
    print(f"Queueing {method} via {comfy_url} (strengths {strengths})...")

    for item in cfg["portraits"]:
        pid = item["id"]
        portrait = portrait_path(pid)
        if portrait is None:
            print(f"  skip missing portrait: {pid}")
            continue
        for strength in strengths:
            dest = OUTPUTS / method / f"{pid}_strength_{strength:.2f}.png"
            dest.parent.mkdir(parents=True, exist_ok=True)
            print(f"  - {pid} @ {strength}")
            queue_workflow(
                comfy_url=comfy_url,
                workflow=workflow,
                portrait_path=portrait,
                upload_path=upload,
                strength=strength,
                output_path=dest,
            )

    write_manifest(upload)
    print(f"\nDone. Manifest -> {MANIFEST_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="PROTOTYPE flux-identity eval harness")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_base = sub.add_parser("baseline", help="Run InSwapper baseline on 5 portraits")
    p_base.add_argument("--upload", type=Path, required=True, help="Visitor selfie")

    p_imp = sub.add_parser("import", help="Import ComfyUI/manual PNGs into outputs/")
    p_imp.add_argument("--method", required=True)
    p_imp.add_argument("--dir", type=Path, required=True)
    p_imp.add_argument("--strength", type=float, default=None)

    sub.add_parser("check", help="Verify gallery files and ComfyUI")

    p_man = sub.add_parser("manifest", help="Rebuild manifest.json from outputs/")
    p_man.add_argument("--upload", type=Path, default=None)

    p_comfy = sub.add_parser("comfy", help="Batch via ComfyUI API (needs workflow JSON)")
    p_comfy.add_argument("--method", required=True, choices=["pulid_inpaint", "instantid_inpaint"])
    p_comfy.add_argument("--upload", type=Path, required=True)
    p_comfy.add_argument("--comfy-url", default=os.environ.get("COMFY_URL", "http://127.0.0.1:8188"))

    args = parser.parse_args()

    if args.cmd == "baseline":
        run_baseline(args.upload)
    elif args.cmd == "import":
        import_outputs(args.method, args.dir, args.strength)
        write_manifest(None)
        print(f"Manifest -> {MANIFEST_PATH}")
    elif args.cmd == "manifest":
        write_manifest(args.upload)
        print(f"Manifest -> {MANIFEST_PATH} ({len(json.loads(MANIFEST_PATH.read_text())['variants'])} variants)")
    elif args.cmd == "check":
        cmd_check()
    elif args.cmd == "comfy":
        if not args.upload.is_file():
            raise SystemExit(f"Upload not found: {args.upload}")
        cmd_comfy(args.method, args.upload, args.comfy_url)


if __name__ == "__main__":
    main()
