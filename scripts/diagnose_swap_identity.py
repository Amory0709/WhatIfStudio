#!/usr/bin/env python3
"""Measure swap identity: cosine(upload, output) vs cosine(portrait, output).

Exit 1 when female-target portraits score materially lower identity than male-target
for the same upload (proxy for "swap onto female face doesn't look like visitor").
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GALLERY = ROOT / "apps" / "web" / "public" / "gallery"
FIXTURES_DIR = ROOT / ".scratch" / "diagnose"
DEFAULT_UPLOAD = FIXTURES_DIR / "my-upload.jpg"
FALLBACK_UPLOAD = ROOT / "prototype" / "flux-identity" / "fixtures" / "prototype-upload.jpg"

# Portrait subject gender (booth gallery audit). Used only to split identity scores.
PORTRAIT_GENDER: dict[str, str] = {
    "tier-1-operating-base-coca-amr-4904": "female",
    "tier-2-people-lab-NEPEC-sugar-land-NAL-7R55891": "female",
    "tier-2-people-armoring-manufacturing-facility-lawrence-nal-6613-4inch": "male",
    "tier-2-people-chx-manufacturing-facility-chemicals-midland-nal-1432-4inch": "male",
    "tier-2-people-chx-production-facility-chemicals-midland-nal-8280-4inch": "male",
    "tier-2-people-chx-production-facility-chemicals-midland-nal-9096-4inch": "male",
    "tier-2-people-chx-production-facility-chemicals-midland-nal-9678-4inch": "male",
    "tier-2-people-chx-production-facility-chemicals-midland-nal-9823-4inch": "male",
    "tier-2-people-drilling-offshore-operations-el-nido-asa-3917-4inch": "male",
    "tier-2-people-land-operations-phitsanulok-asa-2753-4inch": "male",
    "tier-2-people-lead-extrusion-manufacturing-facility-lawrence-nal-6076-2-4inch": "male",
    "tier-2-project-electris-completions-chpc-ardmore-houston-nal-0205-4inch": "male",
    "tier-2-project-electris-completions-chpc-ardmore-houston-nal-0361-4inch": "male",
    "tier-2-project-electris-completions-chpc-ardmore-houston-nal-0434-4inch": "male",
}

IDENTITY_GAP_THRESHOLD = 0.04  # female avg must not trail male avg by more than this


def setup_env() -> None:
    os.environ.setdefault("WHATIF_ENGINE_DIR", str(ROOT / "apps" / "api" / "engine"))
    os.environ.setdefault("GALLERY_DIR", str(GALLERY))
    api_root = str(ROOT / "apps" / "api")
    if api_root not in sys.path:
        sys.path.insert(0, api_root)
    engine = os.environ["WHATIF_ENGINE_DIR"]
    if engine not in sys.path:
        sys.path.insert(0, engine)


def portrait_path(pid: str) -> Path | None:
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = GALLERY / f"{pid}{ext}"
        if p.is_file():
            return p
    return None


def cosine(a, b) -> float:
    import numpy as np

    a = np.asarray(a, dtype=np.float32).ravel()
    b = np.asarray(b, dtype=np.float32).ravel()
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def face_embedding(img_bgr):
    from modules.face_analyser import get_one_face

    face = get_one_face(img_bgr)
    if face is None:
        return None
    return face.normed_embedding


def run(upload: Path) -> list[dict]:
    setup_env()
    import cv2
    import numpy as np
    from app.swap import perform_swap

    upload_bytes = upload.read_bytes()
    upload_img = cv2.imdecode(np.frombuffer(upload_bytes, np.uint8), cv2.IMREAD_COLOR)
    emb_upload = face_embedding(upload_img)
    if emb_upload is None:
        raise SystemExit(f"No face in upload: {upload}")

    gallery_ids = [e["id"] for e in json.loads((ROOT / "data" / "gallery.json").read_text())]
    rows: list[dict] = []

    for pid in gallery_ids:
        src = portrait_path(pid)
        if src is None:
            continue
        portrait_img = cv2.imread(str(src))
        emb_portrait = face_embedding(portrait_img)
        if emb_portrait is None:
            rows.append({"id": pid, "error": "no_face_in_portrait"})
            continue

        out_bytes = perform_swap(str(src), upload_bytes, job_id="diag")
        out_img = cv2.imdecode(np.frombuffer(out_bytes, np.uint8), cv2.IMREAD_COLOR)
        emb_out = face_embedding(out_img)
        if emb_out is None:
            rows.append({"id": pid, "error": "no_face_in_output"})
            continue

        sim_upload = cosine(emb_out, emb_upload)
        sim_portrait = cosine(emb_out, emb_portrait)
        rows.append(
            {
                "id": pid,
                "gender": PORTRAIT_GENDER.get(pid, "unknown"),
                "sim_to_upload": round(sim_upload, 4),
                "sim_to_portrait": round(sim_portrait, 4),
                "identity_margin": round(sim_upload - sim_portrait, 4),
            }
        )
    return rows


def resolve_upload() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).expanduser().resolve()
    if DEFAULT_UPLOAD.is_file():
        return DEFAULT_UPLOAD
    return FALLBACK_UPLOAD


def main() -> int:
    upload = resolve_upload()
    if not upload.is_file():
        print(
            "Upload not found.\n"
            f"  Put your selfie at: {DEFAULT_UPLOAD}\n"
            "  Or run: python scripts/diagnose_swap_identity.py C:\\path\\to\\your-photo.jpg",
            file=sys.stderr,
        )
        return 2

    print(f"upload: {upload}", file=sys.stderr)
    rows = run(upload)
    print(json.dumps(rows, indent=2))

    by_gender: dict[str, list[float]] = {"male": [], "female": []}
    for r in rows:
        if "identity_margin" not in r:
            continue
        g = r.get("gender")
        if g in by_gender:
            by_gender[g].append(r["identity_margin"])

    male_avg = sum(by_gender["male"]) / len(by_gender["male"]) if by_gender["male"] else 0.0
    female_avg = (
        sum(by_gender["female"]) / len(by_gender["female"]) if by_gender["female"] else 0.0
    )
    gap = male_avg - female_avg
    print(
        f"\nidentity_margin avg: male={male_avg:.4f} female={female_avg:.4f} gap={gap:.4f}",
        file=sys.stderr,
    )

    if gap > IDENTITY_GAP_THRESHOLD:
        print(
            f"FAIL: female portraits trail male by {gap:.4f} (> {IDENTITY_GAP_THRESHOLD})",
            file=sys.stderr,
        )
        return 1
    print("PASS: female identity margin within threshold", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
