# Architecture

## Frontend (apps/web, Next.js 14)
- Routes: /, /swap/[id], /print/[id]
- Tailwind + Framer Motion
- **DetailView**: upload archive, phone QR, or **Capture Now** (getUserMedia) → `POST /api/swap`
- Gallery: all portraits (15); prototype eval used a 7-female subset only for testing

## Backend (apps/api, FastAPI)
- `POST /api/swap` — visitor face + `source_id` → watermarked PNG
- **Default booth pipeline** (`facefusion+inswapper`, tuned in prototype):
  - FaceFusion warp + InSwapper 128 ONNX on face crop
  - `WHATIF_SWAP_SOURCE_WEIGHT=0.76` — identity vs gallery expression
  - `WHATIF_PRESERVE_EXPRESSION=0.82` — keep portrait smile (no creepy upload grin)
  - Adaptive hairline feather + face crop paste
- Optional models via `model` / `transfer_face_shape` form fields (HifiFace, HyperSwap, ReSwapper)
- `GET /api/swap/models` — models list + booth tuning values
- Ethics gate: NSFW, face detection, MIME, size (`ethics.py`)
- Watermark via Pillow

## Engine
Vendored Deep-Live-Cam `modules/` + FaceFusion-style ONNX swap (`onnx_swapper.py`).

## Prototype (throwaway)
`prototype/flux-identity/` — eval harness + local `serve.py` for quick tests. **Production uses main API + web UI**, not port 8765.

## Ethics gate
`apps/api/app/ethics.py` refuses any request failing NSFW, face detection, or file validation.
