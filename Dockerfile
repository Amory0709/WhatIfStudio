# syntax=docker/dockerfile:1.7
# Hugging Face Spaces — Docker SDK
# Single image that builds the Next.js static export and the FastAPI backend,
# then runs everything (API + UI) on a single port (7860).

# ----------------------------------------------------------------------------
# Stage 1 — build the Next.js static export
# ----------------------------------------------------------------------------
FROM node:20-alpine AS web-builder
WORKDIR /build

# Install deps with caching
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm install --no-audit --no-fund

# Build
COPY apps/web/ ./
RUN npm run build

# ----------------------------------------------------------------------------
# Stage 2 — runtime: FastAPI + engine + Next.js export
# ----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    WHATIF_ENGINE_DIR=/app/engine \
    GALLERY_DIR=/app/web_out/gallery \
    WEB_OUT_DIR=/app/web_out \
    MAX_UPLOAD_MB=10

# System libs for: opencv-python-headless (libgl1/libglib), insightface
# (libsm/libxext/libxrender), cairosvg (libcairo).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libcairo2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY apps/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# API code + engine (Python modules + assets; models downloaded below)
COPY apps/api/app/ ./app/
COPY apps/api/engine/ ./engine/
COPY apps/api/assets/ ./app/assets/

# Download the swap model at build time. The repo's .gitignore excludes
# apps/api/engine/models/, so HF Spaces (which syncs via git) never receives
# them. We pull from the public Deep-Live-Cam mirror on Hugging Face.
#   - inswapper_128.onnx     — face-swap weights (~265 MB, used at runtime)
# GFPGAN / CoreML models are NOT used by our swap path, so we skip them to
# keep the image lean.
ARG INSWAPPER_URL=https://huggingface.co/hacksider/deep-live-cam/resolve/main/inswapper_128.onnx
RUN mkdir -p /app/engine/models \
    && curl -fL --retry 3 --retry-delay 5 -o /app/engine/models/inswapper_128.onnx "${INSWAPPER_URL}" \
    && ls -la /app/engine/models/

# Pre-built Next.js static export from stage 1
COPY --from=web-builder /build/out/ ./web_out/

# Cloud platforms expose the port through $PORT (HF Spaces → 7860, Fly.io → 8080
# default but we pin it via fly.toml; --port "${PORT:-7860}" keeps both happy).
EXPOSE 7860

# Warm-up note: the first /api/swap call loads InsightFace + the ONNX model
# (10-30s). Hugging Face Spaces sleeps the container after ~15min idle; Fly.io
# is configured for min_machines_running=1 so it stays warm.
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
  CMD python -c "import urllib.request,sys,os; \
p=int(os.environ.get('PORT','7860')); \
sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{p}/health',timeout=5).status==200 else 1)"

# Workers=1: the face-analysis singleton (ethics._FACE_APP_SINGLETON) lives in
# WEB_WORKERS env var controls concurrency (defaults to 1 — safe on 1 GB hosts).
# On a Mac mini or any host with >= 8 GB RAM, set WEB_WORKERS=2 or 3 to handle
# multiple concurrent face-swap requests (each worker loads its own copy of
# InsightFace + ONNX, ~1 GB resident per worker).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860} --workers ${WEB_WORKERS:-1} --proxy-headers"]