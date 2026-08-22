#!/usr/bin/env python3
"""Stage-by-stage identity probe for one portrait (isolates post-swap leakage)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def setup_env() -> None:
    os.environ.setdefault("WHATIF_ENGINE_DIR", str(ROOT / "apps" / "api" / "engine"))
    api = str(ROOT / "apps" / "api")
    if api not in sys.path:
        sys.path.insert(0, api)
    eng = os.environ["WHATIF_ENGINE_DIR"]
    if eng not in sys.path:
        sys.path.insert(0, eng)


def cosine(a, b) -> float:
    import numpy as np

    a = np.asarray(a, dtype=np.float32).ravel()
    b = np.asarray(b, dtype=np.float32).ravel()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def emb(img):
    from modules.face_analyser import get_one_face

    f = get_one_face(img)
    return None if f is None else f.normed_embedding


def margin(out_img, upload_emb, portrait_emb) -> dict:
    e = emb(out_img)
    if e is None:
        return {"error": "no_face"}
    su = cosine(e, upload_emb)
    sp = cosine(e, portrait_emb)
    return {"sim_upload": round(su, 4), "sim_portrait": round(sp, 4), "margin": round(su - sp, 4)}


def probe(portrait: Path, upload: Path) -> None:
    setup_env()
    import cv2
    import numpy as np
    from modules.face_analyser import get_one_face
    from modules import imread_unicode
    from app.onnx_swapper import swap_image, ENV_SOURCE_WEIGHT, BOOTH_SOURCE_WEIGHT
    from app.swap_helpers import (
        extract_face_crop,
        prepare_crop_for_swap,
        harmonize_face_color,
        downscale_image,
        sharpen_crop,
        paste_crop_back,
        adaptive_soft_top_frac,
        ensure_execution_providers,
    )

    ensure_execution_providers()
    upload_bytes = upload.read_bytes()
    upload_img = imread_unicode(str(upload))
    portrait_img = imread_unicode(str(portrait))
    upload_emb = emb(upload_img)
    portrait_emb = emb(portrait_img)
    upload_face = get_one_face(upload_img)
    portrait_face = get_one_face(portrait_img)

    rect, crop = extract_face_crop(portrait_img, portrait_face)
    crop_face = get_one_face(crop) or portrait_face
    work_crop, scale = prepare_crop_for_swap(crop, crop_face)
    work_face = get_one_face(work_crop) or crop_face

    stages: list[tuple[str, object]] = []

    for label, sw in [("onnx_only_w0.88", BOOTH_SOURCE_WEIGHT), ("onnx_only_w1.0", "1.0")]:
        os.environ[ENV_SOURCE_WEIGHT] = sw
        raw = swap_image(
            "inswapper_128",
            upload_img,
            work_crop,
            upload_face,
            work_face,
            full_appearance=False,
        )
        stages.append((label, raw))

    os.environ[ENV_SOURCE_WEIGHT] = BOOTH_SOURCE_WEIGHT
    raw = stages[0][1]
    scaled = downscale_image(raw, scale)
    sharp = sharpen_crop(scaled, strength=None)
    harmonized = harmonize_face_color(sharp, crop)
    top_soft = adaptive_soft_top_frac(crop)
    pasted = paste_crop_back(portrait_img, rect, harmonized, crop, soft_top_frac=top_soft)
    stages.extend(
        [
            ("after_downscale", scaled),
            ("after_sharpen", sharp),
            ("after_harmonize", harmonized),
            (f"after_paste_top{top_soft:.2f}", pasted),
        ]
    )

    print(f"portrait: {portrait.name}")
    for name, img in stages:
        m = margin(img, upload_emb, portrait_emb)
        print(f"  {name:24s} {m}")


def main() -> None:
    gallery = ROOT / "apps" / "web" / "public" / "gallery"
    fixtures = ROOT / ".scratch" / "diagnose"
    default_upload = fixtures / "my-upload.jpg"
    fallback_upload = ROOT / "prototype" / "flux-identity" / "fixtures" / "prototype-upload.jpg"

    if len(sys.argv) > 1:
        upload = Path(sys.argv[1]).expanduser().resolve()
    elif default_upload.is_file():
        upload = default_upload
    else:
        upload = fallback_upload

    if not upload.is_file():
        raise SystemExit(
            "Upload not found.\n"
            f"  Put your selfie at: {default_upload}\n"
            "  Or run: python scripts/diagnose_swap_stages.py C:\\path\\to\\your-photo.jpg"
        )

    female = gallery / "tier-2-people-lab-NEPEC-sugar-land-NAL-7R55891.jpg"
    male = gallery / "tier-2-people-drilling-offshore-operations-el-nido-asa-3917-4inch.jpg"
    print(f"upload: {upload}", file=sys.stderr)
    for p in (female, male):
        probe(p, upload)
        print()


if __name__ == "__main__":
    main()
