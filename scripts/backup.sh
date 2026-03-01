#!/bin/bash
# BRIDGE Backup Script
# Usage: bash scripts/backup.sh [tag]
# Creates timestamped backup of critical files

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:-manual}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$ROOT/backups/${DATE}_${TAG}"

mkdir -p "$BACKUP_DIR"

echo "=== BRIDGE Backup: $BACKUP_DIR ==="

# Core files
cp "$ROOT/api_server.py"        "$BACKUP_DIR/" 2>/dev/null && echo "  api_server.py"
cp "$ROOT/email_templates.py"   "$BACKUP_DIR/" 2>/dev/null && echo "  email_templates.py"
cp "$ROOT/auto_pipeline_v2.py"  "$BACKUP_DIR/" 2>/dev/null && echo "  auto_pipeline_v2.py"
cp "$ROOT/requirements.txt"     "$BACKUP_DIR/" 2>/dev/null && echo "  requirements.txt"
cp "$ROOT/CLAUDE.md"            "$BACKUP_DIR/" 2>/dev/null && echo "  CLAUDE.md"

# Database
cp "$ROOT/master.db"            "$BACKUP_DIR/" 2>/dev/null && echo "  master.db"

# Frontend key files
mkdir -p "$BACKUP_DIR/web_frontend_src"
cp -r "$ROOT/web_frontend/src/app"        "$BACKUP_DIR/web_frontend_src/" 2>/dev/null && echo "  web_frontend/src/app/"
cp -r "$ROOT/web_frontend/src/components" "$BACKUP_DIR/web_frontend_src/" 2>/dev/null && echo "  web_frontend/src/components/"
cp -r "$ROOT/web_frontend/src/lib"        "$BACKUP_DIR/web_frontend_src/" 2>/dev/null && echo "  web_frontend/src/lib/"

# Config files
mkdir -p "$BACKUP_DIR/config"
cp "$ROOT/.claude/security-compliance.md" "$BACKUP_DIR/config/" 2>/dev/null
cp "$ROOT/.claude/coding-style.md"        "$BACKUP_DIR/config/" 2>/dev/null

# Memory
cp -r "$ROOT/.memory" "$BACKUP_DIR/" 2>/dev/null && echo "  .memory/"

# Cleanup: keep only last 10 backups
cd "$ROOT/backups"
ls -dt */ 2>/dev/null | tail -n +11 | xargs rm -rf 2>/dev/null

TOTAL=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "=== Done: $TOTAL ==="
