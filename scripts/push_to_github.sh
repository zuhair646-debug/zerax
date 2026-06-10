#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# Zerax · Auto-push to GitHub
# Reads credentials from /app/backend/.env  (GITHUB_TOKEN, GITHUB_USER, GITHUB_REPO)
# Usage:   bash /app/scripts/push_to_github.sh ["custom commit message"]
# ──────────────────────────────────────────────────────────────────────────────
set -e
cd /app

# Load credentials
source <(grep -E '^GITHUB_(TOKEN|USER|REPO)=' backend/.env | sed 's/^/export /')

if [ -z "$GITHUB_TOKEN" ] || [ -z "$GITHUB_USER" ] || [ -z "$GITHUB_REPO" ]; then
  echo "✗ Missing GitHub config in /app/backend/.env"
  echo "  Required: GITHUB_TOKEN, GITHUB_USER, GITHUB_REPO"
  exit 1
fi

REMOTE_URL="https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${GITHUB_REPO}.git"

# Ensure git identity
git -c user.email=agent@e1.dev -c user.name=E1 config user.email "agent@e1.dev"  2>/dev/null || true
git config user.name  "E1 Agent" 2>/dev/null || true

# Ensure remote points to GitHub
git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE_URL"

# Stage everything new
git add -A

# Commit if there are changes
COMMIT_MSG="${1:-chore: automatic sync from Emergent}"
if ! git diff --cached --quiet; then
  git -c user.email=agent@e1.dev -c user.name="E1 Agent" commit -m "$COMMIT_MSG" --quiet
  echo "✓ Committed: $COMMIT_MSG"
else
  echo "ℹ No new changes to commit"
fi

# Push
echo "→ Pushing to github.com/${GITHUB_USER}/${GITHUB_REPO}.git ..."
if git push -u origin main 2>&1 | tail -3; then
  echo "✓ Push completed"
else
  echo "✗ Push failed"
  exit 1
fi
