"""WhatIf Studio — Gradio app for Hugging Face Spaces (free Gradio SDK tier).

Replaces the FastAPI + Next.js static frontend with a single Gradio UI.
Reuses the existing face-swap engine (`apps/api/engine/`) and gallery
(`apps/web/public/gallery/`).

Run locally:
    WHATIF_ENGINE_DIR=apps/api/engine GALLERY_DIR=apps/web/public/gallery \
        python3 app.py
"""
from __future__ import annotations

import io
import logging
import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent

# Match the env vars the original FastAPI app expects.
os.environ.setdefault("WHATIF_ENGINE_DIR", str(APP_DIR / "apps" / "api" / "engine"))
os.environ.setdefault("GALLERY_DIR", str(APP_DIR / "apps" / "web" / "public" / "gallery"))

# Make `app` package importable (it lives at apps/api/app/).
sys.path.insert(0, str(APP_DIR / "apps" / "api"))

import gradio as gr
from PIL import Image

from app.ethics import validate_face_upload
from app.swap import perform_swap
from app.swap_models import list_models, resolve_default_model
from app.watermark import burn_watermark

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("whatif")

GALLERY_DIR = Path(os.environ["GALLERY_DIR"]).resolve()
SUPPORTED = (".jpg", ".jpeg", ".png", ".webp")


def list_gallery() -> list[str]:
    """Return gallery image paths sorted by filename."""
    return sorted(str(p) for p in GALLERY_DIR.glob("*") if p.suffix.lower() in SUPPORTED)


def swap(source_path: str | None, face_pil: Image.Image | None, model: str) -> Image.Image:
    """Run face-swap. Returns a watermarked PIL Image."""
    if not source_path:
        raise gr.Error("Pick a portrait from the gallery first.")
    if face_pil is None:
        raise gr.Error("Upload your face photo first.")

    # Encode face as bytes for the swap pipeline.
    buf = io.BytesIO()
    face_pil.convert("RGB").save(buf, format="JPEG", quality=92)
    face_bytes = buf.getvalue()

    # NSFW + face-presence check (raises HTTPException on failure).
    try:
        validate_face_upload(face_bytes, "image/jpeg")
    except Exception as e:
        raise gr.Error(f"Upload rejected: {e}")

    log.info("swap: source=%s model=%s upload_size=%d", source_path, model, len(face_bytes))
    try:
        out_bytes = perform_swap(source_path, face_bytes, job_id="gradio-swap", model=model)
    except ValueError as e:
        raise gr.Error(f"Swap failed: {e}")
    except Exception as e:
        log.exception("swap crashed")
        raise gr.Error(f"Engine crashed: {e}")

    try:
        watermarked = burn_watermark(out_bytes)
    except Exception:
        log.exception("watermark failed; returning original")
        watermarked = out_bytes

    return Image.open(io.BytesIO(watermarked))


# ---- Build UI ----

gallery_files = list_gallery()
log.info("gallery: %d images", len(gallery_files))

with gr.Blocks(title="WhatIf Studio", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        "# 🎭 WhatIf Studio\n"
        "Pick a portrait → upload your face → click **Swap**. "
        "Powered by InsightFace + inswapper."
    )

    with gr.Tab("Swap"):
        with gr.Row():
            with gr.Column(scale=1):
                gallery = gr.Gallery(
                    value=gallery_files,
                    label="Step 1 — Pick a portrait",
                    columns=4,
                    height=420,
                    object_fit="cover",
                    allow_preview=False,
                )
            with gr.Column(scale=1):
                face = gr.Image(
                    label="Step 2 — Your face",
                    sources=["upload", "webcam"],
                    type="pil",
                    height=320,
                )
                model_choices = [(m["label"], m["id"]) for m in list_models()]
                swap_model = gr.Dropdown(
                    label="Swap model",
                    choices=model_choices,
                    value=resolve_default_model(),
                )
                result = gr.Image(
                    label="Step 3 — Result",
                    type="pil",
                    height=320,
                    interactive=False,
                )
                btn = gr.Button("Swap", variant="primary", size="lg")

        # Hidden textbox holds the selected portrait path.
        source = gr.Textbox(visible=False)

        def _on_pick(evt: gr.SelectData):
            return gallery_files[evt.index]

        gallery.select(_on_pick, None, source)
        btn.click(swap, inputs=[source, face, swap_model], outputs=result)

    with gr.Tab("About"):
        gr.Markdown(
            "Face-swap demo using **InsightFace** (buffalo_l detection) and "
            "**inswapper_128.onnx** (the open-source Deep-Live-Cam face-swap engine).\n\n"
            "All inference runs on the server. Your face photo is **not** stored — "
            "only the swapped, watermarked output is returned.\n\n"
            f"Gallery: **{len(gallery_files)}** portraits at {GALLERY_DIR}"
        )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", "7860")),
        show_error=True,
    )
