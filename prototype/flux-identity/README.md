# PROTOTYPE: flux-identity eval

> **Integrated into WhatIf Studio.** Production: `npm run dev:win` → pick portrait → **Capture Now** / **Upload Archive** → `POST /api/swap` with booth tuning (`WHATIF_SWAP_SOURCE_WEIGHT=0.76`, `WHATIF_PRESERVE_EXPRESSION=0.82`). This folder is eval-only.

**Question:** PuLID-Flux vs InstantID-Flux vs InSwapper baseline — see `QUESTION.md`.

## Production booth

```powershell
npm run dev:win
```

- Web: http://127.0.0.1:3000
- API: http://127.0.0.1:8000/api/swap
- Tuning: `apps/api/.env.example`, `docs/SWAP-MODELS.md`

## Prototype eval (throwaway)

### Prerequisites

- Gallery JPGs in `apps/web/public/gallery/`
- Your selfie for `--upload`
- **Baseline:** API venv + ONNX weights (`apps/api`)
- **Flux:** ComfyUI + PuLID/InstantID (see `workflows/README.md`)

### Baseline batch

```powershell
python prototype/flux-identity/run.py check
python prototype/flux-identity/run.py baseline --upload C:\path\to\your-face.jpg
```

### Score

Open http://127.0.0.1:8765/eval.html (after `npm run prototype:serve`) or load `manifest.json` in `eval.html`.

```powershell
npm run prototype:serve
```
