# PROTOTYPE question

**Does FaceFusion’s full mask + paste pipeline beat our booth InSwapper path on Identity and Naturalness for female gallery portraits?**

Compare side by side:

1. **booth** — current `perform_swap` (ellipse mask + booth post-process)
2. **ff_native** — same ONNX models, but FaceFusion box + XSeg mask (`face_masker`) and no booth `paste_crop_back` feather
3. **ff_cli** — official [FaceFusion](https://github.com/facefusion/facefusion) `headless-run` (optional; see README)

Fixed upload, female portraits from `portraits-female.json`. Score 1–5 in `eval.html`.

Throwaway — not production.
