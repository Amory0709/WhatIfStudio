# Local development (Windows)

No Hugging Face / cloud needed. Runs on your machine.

## Prerequisites

1. **Python 3.11+** — [python.org](https://www.python.org/downloads/) or:
   ```powershell
   winget install Python.Python.3.12
   ```
   Check **"Add python.exe to PATH"** during install.

2. **Node.js 20+** — already used for the web UI.

3. **Git LFS** — for `inswapper_128.onnx`:
   ```powershell
   git lfs pull
   ```

## Quick start (two terminals)

### Terminal 1 — API (port 8000)

```powershell
cd C:\Projects\MY\WhatIfStudio\apps\api

python -m venv .venv
.\.venv\Scripts\pip install -r requirements-windows.txt

$env:GALLERY_DIR = (Resolve-Path ..\web\public\gallery).Path
$env:WHATIF_ENGINE_DIR = (Resolve-Path .\engine).Path
$env:ALLOWED_ORIGIN = "http://127.0.0.1:3000,http://localhost:3000"

.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Wait until you see `Uvicorn running on http://127.0.0.1:8000`.

First `/api/swap` loads InsightFace + ONNX (~30s). Later swaps faster.

### Terminal 2 — Web UI (port 3000)

```powershell
cd C:\Projects\MY\WhatIfStudio
npm install
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000"
npm --workspace apps/web run dev
```

Open **http://127.0.0.1:3000** → pick portrait → choose swap model → upload face.

### Phone upload (QR code)

Upload Archive can show a QR code so visitors upload from their phone.

Local dev: phone must reach your PC on the LAN (not `localhost`). Before `npm run dev`:

```powershell
$env:NEXT_PUBLIC_PUBLIC_URL = "http://192.168.x.x:3000"   # this PC's LAN IP
$env:ALLOWED_ORIGIN = "http://127.0.0.1:3000,http://localhost:3000,http://192.168.x.x:3000"
```

Phone opens the QR link → `/mobile-upload?session=…` → photo posts to `/api/upload-sessions/…/face`. Booth screen polls until the portrait is ready.

Production / single-port deploy: leave `NEXT_PUBLIC_PUBLIC_URL` unset; QR uses the same origin as the booth.

### Cross-network phone upload (different WiFi / LTE)

LAN IP only works on the same local network. If the phone is on cellular or another WiFi, give both devices a **shared public URL**.

**Option A — Tailscale (recommended for booths / private use)**

1. Install [Tailscale](https://tailscale.com/download) on the booth PC and on the phone; sign in to the same account.
2. On the PC, note the Tailscale IP (often `100.x.x.x`):
   ```powershell
   tailscale ip -4
   ```
3. Start dev with that IP:
   ```powershell
   $ip = tailscale ip -4
   $env:PUBLIC_BASE_URL = "http://${ip}:3000"
   $env:NEXT_PUBLIC_PUBLIC_URL = $env:PUBLIC_BASE_URL
   $env:ALLOWED_ORIGIN = "http://127.0.0.1:3000,http://localhost:3000,$($env:PUBLIC_BASE_URL)"
   ```
4. QR uses the Tailscale URL; phone can be on LTE as long as Tailscale is connected.

**Option B — HTTPS tunnel (quick demos)**

Expose the **web** port (`3000`, not `8000`) so `/mobile-upload` and `/api/*` stay same-origin.

With [ngrok](https://ngrok.com/):

```powershell
# Terminal 1–2: start API + web as usual (scripts/start-local.ps1)

# Terminal 3:
ngrok http 3000
```

Copy the `https://….ngrok-free.app` URL, then restart API + web:

```powershell
$env:PUBLIC_BASE_URL = "https://YOUR-SUBDOMAIN.ngrok-free.app"
$env:NEXT_PUBLIC_PUBLIC_URL = $env:PUBLIC_BASE_URL
$env:ALLOWED_ORIGIN = "http://127.0.0.1:3000,http://localhost:3000,$($env:PUBLIC_BASE_URL)"
```

Regenerate QR (close and reopen Upload Archive). Phone opens the ngrok HTTPS link from anywhere.

Cloudflare Tunnel (`cloudflared tunnel --url http://localhost:3000`) works the same way — set `PUBLIC_BASE_URL` to the printed `https://….trycloudflare.com` URL.

**Option C — Deploy to the cloud (production)**

Ship to Hugging Face Spaces / your server (single origin, port 7860). Booth and phone both hit the same public domain; no tunnel or LAN setup.

## One-click launcher

After Python is installed:

```powershell
cd C:\Projects\MY\WhatIfStudio
.\scripts\start-local.ps1
```

Opens two PowerShell windows (API + web).

## Gradio-only (single port, no Next.js)

Simpler UI on **http://127.0.0.1:7860**:

```powershell
cd C:\Projects\MY\WhatIfStudio\apps\api
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-windows.txt
cd ..\..
.\apps\api\.venv\Scripts\pip install -r requirements.txt

$env:WHATIF_ENGINE_DIR = (Resolve-Path apps\api\engine).Path
$env:GALLERY_DIR = (Resolve-Path apps\web\public\gallery).Path
.\apps\api\.venv\Scripts\python gradio_app.py
```

## Health checks

```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/swap/models
```

## Optional: FaceFusion models (recommended)

```powershell
.\apps\api\.venv\Scripts\python scripts\download_swap_models.py hyperswap_256
```

Then pick **HyperSwap 256 (FaceFusion)** in the UI dropdown (server default when weights present).

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Python was not found` | Install Python 3.12, reopen terminal |
| `insightface` build fails / MSVC required | Use `requirements-windows.txt` not `requirements.txt` |
| `ERR_CONNECTION_REFUSED` on :8000 | API not running — start Terminal 1 with `npm run dev:api:win` |
| Web on :3001 not :3000 | Port 3000 busy — use http://127.0.0.1:3001 |
| `inswapper_128.onnx` missing | `git lfs pull` in repo root |
| No face detected | Ensure `buffalo_l` under `apps/api/engine/models/.insightface/models/` — re-run setup or let InsightFace auto-download |
| CORS / swap fails from web | API must have `ALLOWED_ORIGIN` including `:3000` |
| Phone QR 404 / won't load | QR must not use `127.0.0.1`; set `PUBLIC_BASE_URL` to LAN, Tailscale, or tunnel URL |
| Phone on LTE / other WiFi | Use Tailscale, ngrok, or cloud deploy — see **Cross-network phone upload** above |
| Slow first swap | Normal — model warm-up |
