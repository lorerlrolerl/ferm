#!/bin/bash
# Automated backup script for fermlog database
# Run via cron on the NAS:
#   0 2 * * * /volume1/docker/fermlog/backup.sh >> /volume1/docker/fermlog/logs/backup.log 2>&1

set -e

DB_PATH="/volume1/docker/fermlog/ferm.db"
BACKUP_DIR="/volume1/docker/fermlog/backups"
LOG_DATE=$(date +"%Y-%m-%d %H:%M:%S")
BACKUP_FILE="$BACKUP_DIR/ferm_$(date +%Y%m%d_%H%M%S).db"
KEEP_DAYS=30  # delete backups older than this

# Create backup dir if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check database exists
if [ ! -f "$DB_PATH" ]; then
  echo "[$LOG_DATE] ERROR: database not found at $DB_PATH"
  exit 1
fi

# Copy database (sqlite is safe to copy when not being written to)
# For extra safety, use sqlite3 backup command if available
if command -v sqlite3 &> /dev/null; then
  sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"
else
  cp "$DB_PATH" "$BACKUP_FILE"
fi

# Verify backup was created and has size
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
  SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
  echo "[$LOG_DATE] OK: backup created → $BACKUP_FILE ($SIZE)"
else
  echo "[$LOG_DATE] ERROR: backup file empty or missing"
  exit 1
fi

# Delete old backups
find "$BACKUP_DIR" -name "ferm_*.db" -mtime +$KEEP_DAYS -delete
REMAINING=$(ls "$BACKUP_DIR"/ferm_*.db 2>/dev/null | wc -l)
echo "[$LOG_DATE] Cleanup: $REMAINING backup(s) retained (keeping ${KEEP_DAYS}d)"