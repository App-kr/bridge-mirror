#!/bin/bash
# task_gate.sh — TaskCompleted hook
# exit 2 = 완료 차단 (QA 미통과 시 사용)
# Bridge CLAUDE.md v4.0 FINAL

set -euo pipefail

WORK_ROOT="Q:/Claudework/bridge base"
LOG_DIR="$WORK_ROOT/.logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TASK_NAME="${TASK_NAME:-unknown}"

echo "[$TIMESTAMP] TaskCompleted hook: $TASK_NAME" >> "$LOG_DIR/task_gate.log"

# DB 건수 수호자 체크
python3 -c "
import sqlite3, os, sys
db = '$WORK_ROOT/master.db'
if not os.path.exists(db):
    print('🚨 master.db 없음 — 완료 차단')
    sys.exit(2)
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute('PRAGMA integrity_check')
if cur.fetchone()[0] != 'ok':
    print('🚨 DB 손상 — 완료 차단')
    sys.exit(2)
cur.execute('SELECT COUNT(*) FROM candidates')
c = cur.fetchone()[0]
if c < 3000:
    print(f'🚨 candidates {c} < 3000 — 완료 차단')
    sys.exit(2)
conn.close()
print(f'✅ task_gate 통과: candidates={c}')
" || exit 2

echo "[$TIMESTAMP] task_gate PASS: $TASK_NAME" >> "$LOG_DIR/task_gate.log"
exit 0
