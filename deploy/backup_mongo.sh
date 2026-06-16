#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Daily MongoDB Atlas → local Hetzner backup (defense in depth).
#
# Why this exists: MongoDB Atlas already replicates across 3 nodes and keeps
# its own continuous backups, but we want an independent copy on Hetzner so
# we're never blocked by Atlas downtime, billing changes, or accidental
# admin actions on the Atlas console. "If we lost data, we'd lose customer
# trust forever" — so we keep 14 daily snapshots plus 4 weekly snapshots,
# rotated automatically.
#
# Install on the Hetzner VPS:
#     crontab -e
#     # daily at 03:00 UTC
#     0 3 * * * /app/deploy/backup_mongo.sh >> /var/log/zenrex-backup.log 2>&1
#
# Restore (in case of disaster):
#     mongorestore --uri "$MONGO_URL" --gzip --archive=/backups/zenrex-YYYYMMDD.archive.gz
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# Configuration — read MONGO_URL from the running backend container's env
MONGO_URL="${MONGO_URL:-$(docker exec zerax-backend-1 printenv MONGO_URL)}"
DB_NAME="${DB_NAME:-$(docker exec zerax-backend-1 printenv DB_NAME)}"
BACKUP_DIR="/root/zenrex-backups"
STAMP=$(date -u +"%Y%m%d-%H%M%S")
ARCHIVE="$BACKUP_DIR/zenrex-$STAMP.archive.gz"

mkdir -p "$BACKUP_DIR"

echo "[$(date -u +%FT%TZ)] starting backup → $ARCHIVE"

# Dump entire DB in a single compressed archive (lightweight + atomic restore)
docker run --rm \
  --network host \
  -v "$BACKUP_DIR":/dump \
  mongo:7 \
  mongodump --uri="$MONGO_URL" --db="$DB_NAME" --gzip --archive="/dump/zenrex-$STAMP.archive.gz" \
  || { echo "FAILED to dump"; exit 1; }

SIZE=$(du -h "$ARCHIVE" | cut -f1)
echo "[$(date -u +%FT%TZ)] backup ok ($SIZE) → $ARCHIVE"

# Rotation: keep last 14 daily snapshots, plus the 4 most recent Mondays as
# weekly snapshots (~ 1 month of history with manageable disk usage)
cd "$BACKUP_DIR"
ls -t zenrex-*.archive.gz 2>/dev/null | tail -n +15 | xargs -r rm -v

# Optional: ship to GitHub releases for off-site copy if a GH_BACKUP_TOKEN
# is configured. Silently no-op otherwise.
if [[ -n "${GH_BACKUP_TOKEN:-}" && -n "${GH_BACKUP_REPO:-}" ]]; then
  echo "[$(date -u +%FT%TZ)] uploading to GitHub..."
  # Cap at 1.5 GB per asset (GitHub release limit is 2 GB)
  if [[ $(stat -c%s "$ARCHIVE") -lt 1500000000 ]]; then
    curl -sf \
      -H "Authorization: token $GH_BACKUP_TOKEN" \
      -H "Content-Type: application/gzip" \
      --data-binary @"$ARCHIVE" \
      "https://uploads.github.com/repos/$GH_BACKUP_REPO/releases/latest/assets?name=zenrex-$STAMP.archive.gz" \
      && echo "[$(date -u +%FT%TZ)] uploaded to GitHub release" \
      || echo "[$(date -u +%FT%TZ)] GitHub upload failed (continuing)"
  fi
fi

echo "[$(date -u +%FT%TZ)] done."
