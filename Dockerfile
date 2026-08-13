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
# (libsm/libxext/libxrender), cairosvg (libcairo), watermark text (fonts-dejavu).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libcairo2 \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY apps/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# API code + engine (Python modules + assets; vendored with the engine)
COPY apps/api/app/ ./app/
COPY apps/api/engine/ ./engine/
COPY apps/api/assets/ ./app/assets/

# inswapper_128.onnx and buffalo_l/ are checked into the repo (apps/api/engine/models/)
# and tracked via Git LFS, so the COPY step above already brings them into the image.
# No build-time network fetch needed — first push is ~620 MB slower, but every
# subsequent deploy reuses the same layers and starts immediately.
#
# Models NOT vendored (intentionally):
#   - inswapper_128_fp16.onnx  : only loaded when CUDA GPU is present
#   - inswapper_128_coreml.onnx: only loaded on Apple Silicon native
#   - GFPGANv1.4.pth           : our swap path skips the enhancer
#   - buffalo_l.zip            : we ship the unpacked dir

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