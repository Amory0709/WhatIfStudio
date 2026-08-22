# Face-swap models

WhatIf Studio supports multiple swap backends. Pick one per request in the UI dropdown, or set a server default via `WHATIF_SWAP_MODEL`.

**Default `inswapper_128`** uses the **booth-tuned** FaceFusion + InSwapper path (face crop, portrait expression preserve, adaptive hairline blend). Tuned in `prototype/flux-identity` eval.

## Booth tuning (production defaults)

| Env | Default | Effect |
|-----|---------|--------|
| `WHATIF_SWAP_SOURCE_WEIGHT` | `0.76` | Lower = more gallery smile; higher = more your likeness |
| `WHATIF_PRESERVE_EXPRESSION` | `0.82` | Blends portrait mouth/smile back after swap |
| `WHATIF_SWAP_SHARPNESS` | `0.45` | Post-swap unsharp (0 = off) |

Inspect live values: `GET /api/swap/models` → `source_weight`, `preserve_expression`, `pipeline`.

## Models

| ID | Backend | Likeness | Notes |
|----|---------|----------|-------|
| `inswapper_128` | Deep-Live-Cam | medium | **Default — natural booth look** |
| `reswapper_256` | Deep-Live-Cam | medium+ | Sharper, same soft blend |
| `hififace_256` | FaceFusion | high | Strong likeness; may look uncanny |
| `hyperswap_256` | FaceFusion | high | Max identity; experimental for booth |

## Install weights

From repo root:

```bash
# All models (FaceFusion models also pull xseg_1 occlusion mask)
python scripts/download_swap_models.py

# FaceFusion only
python scripts/download_swap_models.py hyperswap_256 hififace_256
```

Files land in `apps/api/engine/models/`.

## API

```http
GET /api/swap/models
```

```http
POST /api/swap
Content-Type: multipart/form-data

source_id=...
face=<file>
model=inswapper_128   # optional; defaults to WHATIF_SWAP_MODEL or inswapper_128
```

## Env

```env
WHATIF_SWAP_MODEL=inswapper_128
WHATIF_SWAP_SOURCE_WEIGHT=0.76
WHATIF_PRESERVE_EXPRESSION=0.82
WHATIF_SWAP_SHARPNESS=0.45
```

## DreamID note

Original **DreamID** has no self-host inference code (Dreamina web only). **DreamID-V** is video-oriented and needs Wan2.1 + GPU (~16GB+). Not wired into this booth yet — HifiFace/HyperSwap are the practical self-host path for higher likeness.
