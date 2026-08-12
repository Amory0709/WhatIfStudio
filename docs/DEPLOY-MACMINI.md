# Deploying WhatIf Studio on a Mac mini

**Cost:** ¥5/month (electricity). **Cold start:** zero (your Mac is the server).

> Use case: high-frequency demos on a single afternoon where you want Apple
> Silicon's swap speed (~8 s / face) and don't want to pay a cloud bill.
> This is **not** production — there's no SLA, no monitoring, no failover.

## Architecture

```
[visitors on the public Internet]
        │ HTTPS
        ▼
[Cloudflare edge — free tier, DDoS-shielded]
        │ outbound tunnel (no inbound ports exposed on your router)
        ▼
[cloudflared on your Mac mini]  →  [Docker container :7860]
                                       FastAPI + Next.js static
                                       InsightFace + ONNX inswapper
```

Your Mac mini's home IP is **never** exposed. Cloudflare connects out.

## Pre-flight checklist (5 minutes)

On the Mac mini:

| Requirement | Check |
|---|---|
| macOS 13+ (Ventura) on Apple Silicon recommended | `uname -m` → `arm64` |
| ≥ 8 GB RAM free (16 GB recommended) | `top -l 1 \| head -10` |
| ≥ 6 GB free disk | `df -h ~` |
| Homebrew installed | `which brew` |
| Docker Desktop installed & running | `docker info` → "Server: ..." |
| User account can run `sudo pmset` (for disabling sleep) | System Settings → Users & Groups |

## Deploy (15 minutes total)

```bash
# 1. SSH into the Mac mini (or do this on its physical console)
ssh you@macmini.local

# 2. One command — installs cloudflared, builds image, starts container,
#    configures LaunchAgent, prints your public URL
curl -fsSL https://raw.githubusercontent.com/Amory0709/WhatIfStudio/main/infra/macmini/deploy-macmini.sh | bash
```

When it finishes you'll see something like:

```
🎉 WhatIf Studio is live
URL: https://random-three-words.trycloudflare.com
```

Send that URL to anyone in the world — they can use the app immediately.

## Day-of demo checklist

Do these in the morning of your demo:

```bash
# 1. Make sure Docker Desktop is running (whale icon visible in menu bar)
open -a Docker   # only if not running

# 2. Make sure the container + tunnel are up
docker ps --filter name=whatif          # should show "Up ..."
launchctl list | grep whatif            # should show PID for cloudflared

# 3. Verify the public URL still responds
URL=$(cat ~/.whatif-url)
curl -I "$URL/health"                   # expect: HTTP/2 200

# 4. (One-time) Prevent macOS from sleeping during your demo
sudo pmset -a disablesleep 1            # revert with: sudo pmset -a disablesleep 0
caffeinate -di &                        # runs in foreground, Ctrl+C to stop
```

That's it. The first `/api/swap` after a fresh start takes ~30 s (model
warm-up); subsequent swaps are ~8 s on M-series.

## Stable URL with a custom domain (optional, 15 min)

The quick-tunnel URL (`*.trycloudflare.com`) changes every reboot. For a
permanent URL like `https://whatif.yourdomain.com`:

1. Add your domain to Cloudflare (free plan): https://dash.cloudflare.com
   - Cloudflare will scan existing DNS and import records
2. From the Mac mini, log in once:
   ```bash
   cloudflared tunnel login
   # opens browser → pick your domain
   ```
3. Create a named tunnel:
   ```bash
   cloudflared tunnel create whatif
   # prints credentials JSON path, e.g. ~/.cloudflared/<UUID>.json
   ```
4. Create `~/.cloudflared/config.yml`:
   ```yaml
   tunnel: whatif
   credentials-file: /Users/<you>/.cloudflared/<UUID>.json

   ingress:
     - hostname: whatif.yourdomain.com
       service: http://127.0.0.1:7860
     - service: http_status:404
   ```
5. Add DNS route:
   ```bash
   cloudflared tunnel route dns whatif whatif.yourdomain.com
   ```
6. Replace the LaunchAgent template's `ProgramArguments` with:
   ```xml
   <string>__CLOUDFLARED_BIN__</string>
   <string>tunnel</string>
   <string>run</string>
   <string>whatif</string>
   ```
   Then reload:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.whatif.cloudflared.plist
   sed -i '' 's|--url http://127.0.0.1:7860|--no-autoupdate|' ~/Library/LaunchAgents/com.whatif.cloudflared.plist
   # then manually edit to use "tunnel run whatif" instead of "tunnel --url ..."
   launchctl load -w ~/Library/LaunchAgents/com.whatif.cloudflared.plist
   ```

The URL `https://whatif.yourdomain.com` is now permanent.

## Operations

| Action | Command |
|---|---|
| Re-print the public URL | `cat ~/.whatif-url` |
| Tail container logs | `docker logs -f whatif` |
| Tail tunnel logs | `tail -f ~/Library/Logs/whatif/cloudflared.log` |
| Container shell | `docker exec -it whatif /bin/bash` |
| Update to latest code | `./infra/macmini/deploy-macmini.sh` (re-run) |
| Stop everything | `docker rm -f whatif && launchctl unload ~/Library/LaunchAgents/com.whatif.cloudflared.plist` |
| Restart everything | `docker start whatif && launchctl load -w ~/Library/LaunchAgents/com.whatif.cloudflared.plist` |
| Container uses too much RAM | `docker stats whatif` |

## Surviving macOS reboots

| Layer | Auto-restart? | How to verify |
|---|---|---|
| **Mac mini powers back on** | macOS auto-login must be enabled (System Settings → Users & Groups → "Automatically log in as ..."). Otherwise the LaunchAgent never runs. | Reboot and SSH in. |
| **Docker Desktop auto-starts** | Settings → General → ☑ "Start Docker Desktop when you sign in" | Reboot, wait 30 s, run `docker ps` |
| **Container auto-restarts** | Yes — `--restart=unless-stopped` in deploy script. | `docker ps --filter name=whatif` |
| **cloudflared auto-restarts** | Yes — LaunchAgent with `KeepAlive.Crashed = true`. | `launchctl list \| grep whatif` |
| **macOS doesn't sleep** | `sudo pmset -a disablesleep 1` (one-time, persists across reboots) | `pmset -g \| grep sleep` |

## Performance tuning

The default deploy uses **2 workers** (~2 GB resident). Adjust by re-running
the deploy script with `WORKERS` env var:

```bash
WORKERS=4 ./infra/macmini/deploy-macmini.sh
```

| Workers | RAM used | Concurrent swaps | Recommendation |
|---|---|---|---|
| 1 | ~1 GB | 1 at a time | HF Spaces / low-RAM hosts |
| 2 | ~2 GB | 2 at a time | **Default** — comfortable on M4 16 GB |
| 3 | ~3 GB | 3 at a time | M4 Pro / M2 24 GB |
| 4 | ~4 GB | 4 at a time | M2 Ultra / M4 Max |

Each worker loads its own copy of InsightFace + the ONNX model into RAM —
they don't share.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `docker info` hangs | Docker Desktop not running | `open -a Docker`, wait for whale icon to stop animating |
| `brew install cloudflared` slow | First brew run downloads + updates | Wait; subsequent runs are fast |
| Build fails on `pip install` | No network / corporate proxy | Check `curl https://pypi.org` |
| Container starts but `/health` times out | Engine dir empty (models not on disk) | Verify `ls ~/whatifstudio/apps/api/engine/models/` — needs `inswapper_128.onnx` |
| `~/.whatif-url` empty after deploy | cloudflared hasn't connected yet | `tail -f ~/Library/Logs/whatif/cloudflared.log` and look for "Your quick Tunnel has been created" |
| Public URL returns 502 | Container died after deploy | `docker logs whatif` to see why; restart with `docker start whatif` |
| Mac mini goes to sleep during demo | `pmset disablesleep` not set | `sudo pmset -a disablesleep 1` |
| `cairosvg` import error in container | macOS build env vs Linux runtime mismatch | Rebuild with `docker build --no-cache -t whatif .` |
| Container OOM-killed | Too many workers for available RAM | Lower `WORKERS=1` in the deploy script |

## What this is NOT for

- Multi-region production (no failover)
- High SLA (no monitoring, no paging)
- Sensitive data (Cloudflare sees all uploads; consider self-hosting with TLS cert for true end-to-end encryption)
- 24/7 uptime under home-network flakiness

For those, see [DEPLOY-ORACLE.md](DEPLOY-ORACLE.md) (free, but slower) or
[README.md](../README.md) §"Deploy" (paid cloud options).