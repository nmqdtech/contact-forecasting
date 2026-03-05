#!/bin/bash
set -euo pipefail
BACKUP_DIR="/home/najib/backups/postgres"
mkdir -p "$BACKUP_DIR"
FILENAME="forecasting-$(date +%Y%m%d-%H%M%S).sql.gz"
docker exec forecasting-db pg_dump -U forecasting forecasting \
  | gzip > "$BACKUP_DIR/$FILENAME"
# Retain last 14 days only
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +14 -delete
echo "[$(date)] Backup complete: $BACKUP_DIR/$FILENAME"
