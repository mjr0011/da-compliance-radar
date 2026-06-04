#!/usr/bin/env bash
#
# Postgres backup for D&A Compliance Radar.
#
# Runs `pg_dump`, gzips the output, optionally uploads to S3, and writes
# a manifest with checksums.
#
# Recommended cron line (3 AM Europe/London):
#   0 3 * * * /opt/da-radar/scripts/backup.sh >> /var/log/da-radar-backup.log 2>&1
#
# Required env vars (read from the same .env the stack uses):
#   POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
#
# Optional env vars:
#   BACKUP_DIR              local destination (default: /var/backups/da-radar)
#   BACKUP_RETENTION_DAYS   prune local backups older than this (default: 14)
#   S3_BUCKET               s3 bucket name (e.g. da-radar-backups) — uploads if set
#   S3_PREFIX               prefix inside the bucket (default: postgres/)
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION  for S3 upload
#
# To restore:
#   gunzip -c BACKUP_FILE.sql.gz | PGPASSWORD=$POSTGRES_PASSWORD \
#     psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB
#
set -euo pipefail

# --- Defaults ---
BACKUP_DIR="${BACKUP_DIR:-/var/backups/da-radar}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
S3_PREFIX="${S3_PREFIX:-postgres/}"

# --- Validation ---
for v in POSTGRES_HOST POSTGRES_PORT POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB; do
  if [ -z "${!v:-}" ]; then
    echo "ERROR: $v is not set" >&2
    exit 1
  fi
done

mkdir -p "$BACKUP_DIR"
TS="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
OUT="$BACKUP_DIR/da-radar-${TS}.sql.gz"
MANIFEST="$BACKUP_DIR/da-radar-${TS}.manifest.json"

echo "[$(date -u +%FT%TZ)] Starting backup → $OUT"

# --- Dump + gzip in one pipeline ---
# --no-owner / --no-acl keep restores portable across roles.
# --clean adds DROP statements so a restore into an existing DB works.
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
  --host="$POSTGRES_HOST" \
  --port="$POSTGRES_PORT" \
  --username="$POSTGRES_USER" \
  --dbname="$POSTGRES_DB" \
  --no-owner --no-acl --clean --if-exists \
  | gzip -9 > "$OUT"

SIZE=$(stat -c%s "$OUT")
SHA256=$(sha256sum "$OUT" | cut -d' ' -f1)

cat > "$MANIFEST" <<EOF
{
  "timestamp_utc": "$(date -u +%FT%TZ)",
  "filename": "$(basename "$OUT")",
  "size_bytes": $SIZE,
  "sha256": "$SHA256",
  "database": "$POSTGRES_DB",
  "host": "$POSTGRES_HOST",
  "tool": "pg_dump",
  "retention_days": $BACKUP_RETENTION_DAYS
}
EOF

echo "[$(date -u +%FT%TZ)] Backup written ($SIZE bytes, sha256 ${SHA256:0:12}…)"

# --- Optional S3 upload ---
if [ -n "${S3_BUCKET:-}" ]; then
  if ! command -v aws >/dev/null 2>&1; then
    echo "WARNING: S3_BUCKET set but aws CLI not installed; skipping upload" >&2
  else
    echo "[$(date -u +%FT%TZ)] Uploading to s3://$S3_BUCKET/$S3_PREFIX"
    aws s3 cp "$OUT"      "s3://$S3_BUCKET/$S3_PREFIX$(basename "$OUT")"      --storage-class STANDARD_IA
    aws s3 cp "$MANIFEST" "s3://$S3_BUCKET/$S3_PREFIX$(basename "$MANIFEST")" --content-type application/json
    echo "[$(date -u +%FT%TZ)] S3 upload complete"
  fi
fi

# --- Prune old local backups ---
if [ -d "$BACKUP_DIR" ]; then
  find "$BACKUP_DIR" -name 'da-radar-*.sql.gz' -mtime "+$BACKUP_RETENTION_DAYS" -delete
  find "$BACKUP_DIR" -name 'da-radar-*.manifest.json' -mtime "+$BACKUP_RETENTION_DAYS" -delete
fi

echo "[$(date -u +%FT%TZ)] Done."
