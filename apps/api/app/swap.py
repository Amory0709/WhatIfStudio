"""Wrap Deep-Live-Cam's swap functions as a simple API."""
from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

ENGINE_DIR = Path(os.environ.get("WHATIF_ENGINE_DIR", ".")).resolve()
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))


def perform_swap(source_path: str, face_bytes: bytes, job_id: str) -> bytes:
    """Composite face_bytes onto source_path and return a PNG."""
    from modules import globals as g
    from modules.processors.frame import face_swapper

    g.opacity = 1.0
    g.many_faces = False
    g.map_faces = False

    if not face_swapper.pre_start():
        raise ValueError("Face-swap model not loaded — check engine/models/ for inswapper_128.onnx")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src_face_path = tmp_path / "face.jpg"
        src_face_path.write_bytes(face_bytes)

        target_path = tmp_path / "target.png"
        target_path.write_bytes(Path(source_path).read_bytes())

        try:
            face_swapper.process_frames(
                source_path=str(src_face_path),
                temp_frame_paths=[str(target_path)],
            )
        except Exception as e:
            raise ValueError(f"Swap engine failed: {e}") from e

        out_bytes = Path(target_path).read_bytes()

    arr = cv2.imdecode(np.frombuffer(out_bytes, np.uint8), cv2.IMREAD_COLOR)
    if arr is None:
        raise ValueError("Swap produced no image")

    ok, buf = cv2.imencode(".png", arr)
    if not ok:
        raise ValueError("Failed to encode swap output")
    return buf.tobytes()
