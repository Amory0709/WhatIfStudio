# Deploying to Oracle Cloud Always Free Tier

**Cost:** $0/month, forever (the "Always Free" tier never expires).

**Limits:** 2 OCPU + 12 GB RAM ARM total (across all A1 instances in your
tenancy); 200 GB block storage; 10 TB/month egress. Plenty for this app
(~1 GB resident at runtime, ~3 GB peak during build).

**Tradeoffs vs Fly.io:**
- ✅ Actually free
- ✅ Plenty of RAM (12 GB vs Fly.io's 1 GB shared)
- ❌ Needs credit card for signup verification
- ❌ "Out of host capacity" errors common in popular regions (Phoenix,
  Frankfurt, Ashburn) — try Seoul/Tokyo/Sydney or retry
- ❌ Manual provisioning via web UI
- ❌ Free-tier users get no Oracle Support tickets

## Setup (~15 min)

```bash
# 1. Sign up at https://cloud.oracle.com/free (requires credit card; no charge)

# 2. Console → Compute → Instances → Create Instance
#    - Name: whatif-studio
#    - Image: Ubuntu 22.04 (aarch64)
#    - Shape: VM.Standard.A1.Flex  →  2 OCPU, 12 GB RAM  (the Always Free max)
#    - Networking: create a new VCN + public subnet (defaults are fine)
#    - Download the SSH key

# 3. SSH in (replace with your public IP and key path)
ssh -i ~/Downloads/ssh-key-*.key ubuntu@<PUBLIC_IP>

# 4. Open ports 80 + 443 in the VCN's security list (Oracle blocks by default)
#    Networking → Virtual Cloud Networks → your VCN → Subnet → Security List
#    Add Ingress Rule: 0.0.0.0/0 TCP 80, TCP 443

# 5. One-liner install + run
sudo apt update && sudo apt install -y docker.io
sudo usermod -aG docker ubuntu && newgrp docker
cd /tmp
git clone https://github.com/<YOUR-USER>/whatifstudio.git
cd whatifstudio
docker build -t whatif .    # 4–6 min
docker run -d --name whatif --restart=always -p 80:7860 whatif

# 6. (Optional) HTTPS via Caddy
sudo apt install -y caddy
echo "your-domain.com { reverse_proxy 127.0.0.1:7860 }" \
  | sudo tee /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Visit `http://<PUBLIC_IP>`. Bind a domain → Caddy auto-issues Let's Encrypt cert.

## Gotchas

- **Out of capacity** is the #1 issue. Try smaller regions; if it persists,
  use Hetzner Cloud CX22 (€3.29/mo) as a paid fallback.
- **Do not exceed 2 OCPU / 12 GB total** across all your A1 shapes — instances
  get disabled and deleted after 30 days if you do.
- **Free tier gets no Support tickets.** Community-only (Reddit
  r/oraclecloud, Stack Overflow).
- **Always Free resources may be reclaimed for prolonged inactivity** (Oracle
  hints at this in the FAQ; no specific time period documented).

## Tearing down

Stop the VM (don't delete the Always Free tenancy):
```bash
# Inside the VM
docker rm -f whatif

# From Oracle Console
Compute → Instances → whatif-studio → Stop (don't terminate, or you lose
the Always Free allocation)
```