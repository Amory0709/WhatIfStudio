---
title: WhatIf Studio
emoji: 🎭
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# WhatIf Studio

A monorepo demo that lets visitors **swap their face onto fictional gallery portraits** using a local face-swap engine, then walk away with a watermarked print. Built as a blue-and-white minimalist "art gallery" experience — every card is pre-selected, the centerpiece is a giant floating numeral, and the result page prints out on a slot-fed printer with a `SLB` watermark.

## Stack

- **Web** `apps/web` — Next.js 14 (App Router) + React + Tailwind v3 + framer-motion
- **API** `apps/api` — FastAPI + Python 3.12 + [Deep-Live-Cam](https://github.com/hacksider/Deep-Live-Cam) face-swap engine (vendored under `apps/api/engine/`)
- **Swap engine** — runs on CPU via InsightFace (det_10g + w600k_r50 landmarks) and an ONNX inswapper model; one swap takes ~30 s on M-series Mac

## Layout

```
whatifstudio/
├── apps/
│   ├── web/                       Next.js front-end
│   │   ├── app/                   App Router pages (/, /swap/[id], /print/[id])
│   │   ├── components/ag/         Gallery / Detail / Result views + StudioShell
│   │   ├── public/gallery/        Portrait JPEGs (see apps/web/public/gallery/README.md)
│   │   └── public/fonts/          SLBSans Regular + Bold (vendored woff2)
│   └── api/                       FastAPI back-end
│       ├── app/
│       │   ├── main.py            /health + /api/swap + CORS middleware
│       │   ├── swap.py            Engine wrapper (Deep-Live-Cam modules)
│       │   ├── ethics.py          Upload validation
│       │   └── watermark.py       Burn SLB watermark onto the swap output
│       └── engine/                Vendored swap engine (modules + models)
└── .gitignore
```

## Running locally

```bash
# API (port 8000)
cd apps/api
WHATIF_ENGINE_DIR=$(pwd)/engine ./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# Web (port 3000)
cd apps/web
../../node_modules/.bin/next dev --port 3000
```

Then open <http://127.0.0.1:3000>. Pick a portrait, upload a face photo (or capture from your webcam), wait ~30 s for the swap, then `Print Portrait` to download the watermarked result.

## Face-swap endpoint

`POST /api/swap` — multipart form
- `source_id`: artwork id, e.g. `amber-1`
- `face`: the user's face JPEG/PNG

Response: a watermarked PNG with `X-WhatIf-Job` and `X-WhatIf-Watermarked` headers.

CORS is enabled for `http://localhost:3000`, `http://127.0.0.1:3000`, and IPv6 `[::1]:3000` by default — override with the `ALLOWED_ORIGIN` env var (comma-separated) in production.

## Design notes

- The homepage is a 3D dual-circle "infinity loop" gallery. 50 cards are placed on the surface of two interlocked tori; the camera sits above and looks down at `rotateX(-35deg)`. A 1800-px blue `1` floats under the camera as the visual focal point.
- All motion uses framer-motion springs; the printer animation slides the printed portrait from `y: -100%` to its resting place over 4 seconds, then reveals the `Download Print` and `Back to Homepage` actions below.
- Fonts are vendored `SLBSans` (Regular + Bold woff2) from the SLB 100 Family Day repository — no Google Fonts CDN traffic.

## 🚀 Deploy

The repo ships with a multi-stage `Dockerfile` (builds Next.js, then packages with FastAPI on port 7860) and platform configs for the two cheapest reasonable targets.

### Option A — Fly.io (recommended, ~$2/month, HR-friendly)

```bash
brew install flyctl            # or: curl -L https://fly.io/install.sh | sh
fly auth signup                # browser pop-up for login
fly launch --copy-config       # reads fly.toml — skip Postgres when asked
fly deploy                     # builds + pushes + releases (~4 min)
fly open                       # → https://whatif-studio.fly.dev
```

Then in the Fly.io dashboard → **GitHub → Connect** for one-click redeploy on every push. Custom domain is one command: `fly certs add yourdomain.com`.

### Option B — Hugging Face Spaces (free, but Docker SDK is paid now)

Only Static SDK is free on HF; Docker/Gradio require a paid plan. Use Fly.io above.

### Option C — Oracle Cloud Always Free (truly free, ~15 min setup)

2 OCPU / 12 GB RAM ARM instance, **permanently**. CC required for signup. The "out of host capacity" error is common in popular regions — try Seoul/Tokyo/Sydney first. See [docs/DEPLOY-ORACLE.md](docs/DEPLOY-ORACLE.md).

### Option D — Any Docker host (Hetzner CX22 €3.29/mo, DO $4/mo, Vultr $5/mo, etc.)

Same `Dockerfile` works everywhere:
```bash
docker build -t whatif . && docker run -d -p 80:7860 --name whatif --restart=always whatif
```

### Option E — Your own Mac mini (¥5/month electricity, fastest swap speed)

Best for a single-day high-frequency demo. Apple Silicon runs InsightFace +
ONNX ~5× faster than a shared cloud CPU. Uses [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
so no port forwarding needed.

One command on the Mac mini:
```bash
curl -fsSL https://raw.githubusercontent.com/Amory0709/WhatIfStudio/main/infra/macmini/deploy-macmini.sh | bash
```

See [docs/DEPLOY-MACMINI.md](docs/DEPLOY-MACMINI.md) for the full plan,
operations guide, and custom-domain setup.
