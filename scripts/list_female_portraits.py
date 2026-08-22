#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

import cv2
import insightface

ROOT = Path(__file__).resolve().parents[1]
GALLERY = ROOT / "apps" / "web" / "public" / "gallery"
os.environ.setdefault("WHATIF_ENGINE_DIR", str(ROOT / "apps" / "api" / "engine"))
root = Path(os.environ["WHATIF_ENGINE_DIR"]) / "models" / ".insightface"
app = insightface.app.FaceAnalysis(
    name="buffalo_l",
    root=str(root),
    providers=["CPUExecutionProvider"],
    allowed_modules=["detection", "genderage"],
)
app.prepare(ctx_id=0, det_size=(640, 640))

for path in sorted(GALLERY.glob("*.jpg")):
    img = cv2.imread(str(path))
    faces = app.get(img)
    if not faces:
        print(f"no_face\t{path.stem}")
        continue
    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    gender = "female" if face.gender == 0 else "male"
    print(f"{gender}\t{path.stem}")
