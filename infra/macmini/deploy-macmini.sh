#!/usr/bin/env bash
# deploy-macmini.sh — One-shot deploy WhatIf Studio on a Mac mini.
#
# What it does (in order):
#   1. Pre-flight: macOS + Homebrew + Docker (or install guide)
#   2. Install cloudflared via Homebrew
#   3. Pull the latest repo (clones to ~/whatifstudio if missing)
#   4. docker build the production image (4-6 min on Apple Silicon)
#   5. Start the container with --restart=unless-stopped and 2 workers
#      (1 GB resident per worker, ~2 GB total — fine on a 16 GB M-series)
#   6. Start a Cloudflare quick tunnel (no account needed; URL written to
#      ~/.whatif-url so you can re-read it any time)
#   7. Install a LaunchAgent so cloudflared auto-restarts on boot / crash
#   8. Print health-check + how-to-stop commands
#
# Idempotent: safe to re-run; it pulls latest, rebuilds, swaps the container.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/Amory0709/WhatIfStudio/main/infra/macmini/deploy-macmini.sh | bash
#   # or, locally:
#   ./infra/macmini/deploy-macmini.sh

set -euo pipefail

REPO_URL="https://github.com/Amory0709/WhatIfStudio.git"
WHATIF_HOME="$HOME/whatifstudio"
CONTAINER_PORT=7860
WORKERS=2   # tuned for high-frequency demos; bump to 3-4 on 32 GB+ machines
LOG_DIR="$HOME/Library/Logs/whatif"

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
blue()  { printf '\033[34m%s\033[0m\n' "$*"; }

step() { blue "==> $*"; }
ok()   { green "✓ $*"; }
die()  { red "✗ $*" >&2; exit 1; }

# ---------- 1. preflight ------------------------------------------------------
step "1/8  preflight: macOS + Homebrew"
[ "$(uname -s)" = "Darwin" ] || die "Run on macOS (you're on $(uname -s))"
arch=$(uname -m)
ok "macOS detected, arch=$arch"

which brew >/dev/null 2>&1 || die "Homebrew missing — install from https://brew.sh first"
ok "Homebrew found at $(which brew)"

# ---------- 2. docker ---------------------------------------------------------
step "2/8  Docker Desktop"
if ! command -v docker >/dev/null 2>&1; then
  cat <<EOF

Docker Desktop not found. Install it with:

    brew install --cask docker

Then:
  1. Launch Docker Desktop from Applications (or run: open -a Docker)
  2. Accept the license (one-time)
  3. Wait until the whale icon in the menu bar stops animating
  4. Re-run this script: ./infra/macmini/deploy-macmini.sh

EOF
  exit 0
fi

# Check daemon is up, not just CLI installed
if ! docker info >/dev/null 2>&1; then
  die "Docker CLI present but daemon not responding. Open Docker Desktop and retry."
fi
ok "Docker $(docker version --format '{{.Server.Version}}') running"

# ---------- 3. cloudflared ----------------------------------------------------
step "3/8  cloudflared"
if ! command -v cloudflared >/dev/null 2>&1; then
  brew install cloudflared
fi
CLOUDFLARED_BIN=$(command -v cloudflared)
ok "cloudflared at $CLOUDFLARED_BIN"

# ---------- 4. clone / pull ---------------------------------------------------
step "4/8  fetching repo → $WHATIF_HOME"
if [ -d "$WHATIF_HOME/.git" ]; then
  (cd "$WHATIF_HOME" && git pull --ff-only) || die "git pull failed — resolve conflicts in $WHATIF_HOME then retry"
else
  [ -d "$WHATIF_HOME" ] && die "$WHATIF_HOME exists but isn't a git repo — remove or rename it, then retry"
  git clone "$REPO_URL" "$WHATIF_HOME"
fi
ok "repo at HEAD $(git -C "$WHATIF_HOME" rev-parse --short HEAD)"

# ---------- 5. docker build ---------------------------------------------------
step "5/8  docker build (4-6 min on Apple Silicon)"
docker build -t whatif "$WHATIF_HOME"
ok "image built: whatif"

# ---------- 6. run container --------------------------------------------------
step "6/8  starting container (workers=$WORKERS, auto-restart)"
docker rm -f whatif 2>/dev/null || true
docker run -d \
  --name whatif \
  --restart=unless-stopped \
  -p 127.0.0.1:$CONTAINER_PORT:$CONTAINER_PORT \
  -v "$WHATIF_HOME/apps/web/public/gallery:/gallery:ro" \
  -v "$WHATIF_HOME/apps/api/engine:/engine:ro" \
  -e WEB_WORKERS="$WORKERS" \
  whatif

# Wait for /health (InsightFace + ONNX cold start can take ~30s)
printf "  waiting for /health"
for i in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:$CONTAINER_PORT/health" >/dev/null 2>&1; then
    printf " ready\n"
    ok "container healthy"
    break
  fi
  printf "."
  sleep 1
  [ $i -eq 60 ] && { printf "\n"; die "/health did not respond in 60s — check: docker logs whatif"; }
done

# ---------- 7. cloudflare tunnel ----------------------------------------------
step "7/8  starting Cloudflare quick tunnel (no account needed)"

mkdir -p "$LOG_DIR"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_AGENTS"

# Substitute the actual binary path into the template
TEMPLATE="${WHATIF_HOME}/infra/macmini/com.whatif.cloudflared.plist.template"
PLIST="$LAUNCH_AGENTS/com.whatif.cloudflared.plist"
sed "s|__CLOUDFLARED_BIN__|$CLOUDFLARED_BIN|g; s|__LOG_DIR__|$LOG_DIR|g" \
  "$TEMPLATE" > "$PLIST"

# Stop any running tunnel (LaunchAgent, manual, whatever)
pkill -f "cloudflared.*--url.*$CONTAINER_PORT" 2>/dev/null || true
launchctl unload "$PLIST" 2>/dev/null || true
sleep 1

# Load the LaunchAgent — it starts tunnel on launch, auto-restarts on crash
launchctl load -w "$PLIST"
sleep 5

# Extract the random URL from cloudflared's startup banner
LOG="$LOG_DIR/cloudflared.log"
for i in $(seq 1 30); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" 2>/dev/null | head -1 || true)
  [ -n "$URL" ] && break
  sleep 1
done

[ -n "${URL:-}" ] || die "cloudflared didn't print a URL in 30s — check: tail -f $LOG"

echo "$URL" > "$HOME/.whatif-url"
ok "tunnel live → $URL"

# ---------- 8. summary --------------------------------------------------------
step "8/8  done"
cat <<EOF

  ┌────────────────────────────────────────────────────┐
  │ 🎉 WhatIf Studio is live                          │
  │                                                    │
  │ URL:        $(printf '%-39s' "$URL")│
  │ Container:  docker ps --filter name=whatif         │
  │ Logs:       docker logs -f whatif                  │
  │ Tunnel log: tail -f $LOG_DIR/cloudflared.log       │
  │ Re-print:   cat ~/.whatif-url                      │
  │                                                    │
  │ Update:     ./infra/macmini/deploy-macmini.sh      │
  │ Stop:       docker rm -f whatif                    │
  └────────────────────────────────────────────────────┘

Notes:
  • First /api/swap call loads InsightFace + ONNX (~30s); subsequent swaps ~8s on M-series.
  • The trycloudflare URL changes every time cloudflared restarts (e.g. reboot).
    For a stable URL like https://whatif.yourdomain.com, follow docs/DEPLOY-MACMINI.md
    §"Stable URL with a custom domain".
  • To survive macOS reboots: System Settings → General → Login Items → enable
    Docker Desktop. Container is configured --restart=unless-stopped.

EOF