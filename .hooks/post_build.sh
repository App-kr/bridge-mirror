#!/bin/bash
# post_build.sh — Stop hook (빌드 후 자동 실행)
# Bridge CLAUDE.md v4.0 FINAL

set -euo pipefail

WORK_ROOT="Q:/Claudework/bridge base"
LOG_DIR="$WORK_ROOT/.logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "[$TIMESTAMP] post_build START" >> "$LOG_DIR/post_build.log"

# 1. API 컴파일 검증
echo "--- API compile check ---"
python3 -m py_compile "$WORK_ROOT/api_server.py" && echo "✅ api_server.py OK" || {
    echo "🚨 api_server.py 컴파일 실패" >> "$LOG_DIR/post_build.log"
    exit 1
}

# 2. f-string SQL 주입 검사
FSTRING_COUNT=$(grep -c 'f".*{' "$WORK_ROOT/api_server.py" 2>/dev/null || echo 0)
if [ "$FSTRING_COUNT" -gt 0 ]; then
    echo "🚨 f-string SQL 감지: $FSTRING_COUNT 건 — 배포 BLOCK"
    echo "[$TIMESTAMP] BLOCK: f-string SQL $FSTRING_COUNT 건" >> "$LOG_DIR/post_build.log"
    exit 2
fi
echo "✅ f-string SQL 검사: 0건 (PASS)"

# 3. DB 무결성
python3 -c "
import sqlite3
conn = sqlite3.connect('$WORK_ROOT/master.db')
cur = conn.cursor()
cur.execute('PRAGMA integrity_check')
result = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM candidates')
c = cur.fetchone()[0]
conn.close()
assert result == 'ok', f'DB 손상: {result}'
assert c >= 3000, f'candidates {c} < 3000'
print(f'✅ DB OK: candidates={c}')
" || exit 2

echo "[$TIMESTAMP] post_build PASS" >> "$LOG_DIR/post_build.log"
echo "✅ post_build 완료 — 배포 가능"
exit 0
