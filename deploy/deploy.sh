#!/usr/bin/env bash
# Zenrex Quick Deploy Script — Deploy React + backend to Hetzner VPS in ~60s.
# Usage: bash /app/deploy/deploy.sh [domain]
#   Example: bash /app/deploy/deploy.sh zenrex.ai
set -e

DOMAIN="${1:-zenrex.ai}"
VPS_IP="91.98.154.148"
SSH_KEY="/root/.ssh/zerax_deploy"
SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=no root@$VPS_IP"

echo "🚀 Deploying Zenrex to $DOMAIN ($VPS_IP)..."

# 1) Build React with target backend URL
cd /app/frontend
echo "📦 Building React (REACT_APP_BACKEND_URL=https://$DOMAIN)..."
REACT_APP_BACKEND_URL="https://$DOMAIN" yarn build > /tmp/zenrex_build.log 2>&1
find build -name "*.map" -delete
echo "✓ Build done ($(du -sh build | cut -f1))"

# 2) Sync build + backend code to VPS
echo "📤 Syncing to VPS..."
rsync -az --no-perms --no-owner --no-group --delete -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
  /app/frontend/build/ root@$VPS_IP:/opt/zerax/frontend/build/ > /dev/null
rsync -az --no-perms --no-owner --no-group --delete \
  --exclude="backups/" --exclude="__pycache__/" --exclude="*.pyc" \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
  /app/backend/ root@$VPS_IP:/opt/zerax/backend/ > /dev/null
echo "✓ Files synced"

# 3) Hot-reload Nginx (no downtime)
$SSH 'nginx -t > /dev/null 2>&1 && systemctl reload nginx' && echo "✓ Nginx reloaded"

# 4) Backend restart (only needed if backend code or .env changed)
$SSH 'cd /opt/zerax && docker compose restart backend > /dev/null' && echo "✓ Backend restarted"

# 5) Health check
sleep 8
HEALTH=$(curl -s -m 5 "http://$VPS_IP/api/store/health")
if [[ "$HEALTH" == *"ok\":true"* ]]; then
  echo "✓ Health check passed: $HEALTH"
  echo ""
  echo "🎉 Deployed! https://$DOMAIN (or http://$VPS_IP)"
else
  echo "✗ Health check failed: $HEALTH"
  exit 1
fi
