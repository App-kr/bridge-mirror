"""
migrate_community_to_supabase.py
SQLite community_posts → Supabase 1회성 마이그레이션

실행:
  cd "Q:\Claudework\bridge base"
  python migrations/migrate_community_to_supabase.py

주의:
  - Supabase에 community_posts 테이블이 먼저 생성되어 있어야 함
    (migrations/supabase_community_posts.sql 먼저 실행)
  - 중복 실행 시 기존 데이터 위에 추가됨 → 한 번만 실행할 것
"""
import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

# .env 로딩
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

SUPABASE_URL     = os.getenv("SUPABASE_URL", "")
SUPABASE_SVC_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
DB_PATH          = os.getenv("DB_PATH", os.getenv("BRIDGE_DB_PATH",
                   str(Path(__file__).resolve().parent.parent / "master.db")))

if not SUPABASE_URL or not SUPABASE_SVC_KEY:
    print("ERROR: .env에 SUPABASE_URL 및 SUPABASE_SERVICE_KEY가 필요합니다.")
    sys.exit(1)

if not Path(DB_PATH).exists():
    print(f"ERROR: master.db 없음 → {DB_PATH}")
    sys.exit(1)

try:
    from supabase import create_client
except ImportError:
    print("ERROR: pip install supabase")
    sys.exit(1)

svc = create_client(SUPABASE_URL, SUPABASE_SVC_KEY)

# ── SQLite 읽기 ──────────────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT * FROM community_posts WHERE is_deleted=0 ORDER BY id"
).fetchall()
conn.close()
print(f"SQLite 게시물: {len(rows)}건")

if not rows:
    print("마이그레이션할 데이터가 없습니다.")
    sys.exit(0)

# ── Supabase 현재 건수 확인 ───────────────────────────────────────────────────
existing = svc.table('community_posts').select('id', count='exact').execute()
existing_count = existing.count or 0
if existing_count > 0:
    print(f"⚠️  Supabase에 이미 {existing_count}건 존재합니다.")
    confirm = input("계속 진행하면 중복 데이터가 생길 수 있습니다. 계속? (yes/no): ").strip()
    if confirm.lower() != 'yes':
        print("취소됨.")
        sys.exit(0)

# ── 변환 및 삽입 ──────────────────────────────────────────────────────────────
def normalize_ts(ts: str | None) -> str:
    """SQLite datetime → ISO 8601 UTC 변환"""
    if not ts:
        return datetime.now(timezone.utc).isoformat()
    try:
        # "2026-01-15 10:30:00" 형식 처리
        if 'T' not in ts and '+' not in ts and 'Z' not in ts:
            ts = ts.replace(' ', 'T') + '+00:00'
        return ts
    except Exception:
        return datetime.now(timezone.utc).isoformat()

posts = []
for r in rows:
    posts.append({
        'board':        r['board'],
        'title':        r['title'] or '',
        'body':         r['body'] or '',
        'author_hash':  r['author_hash'] or '',
        'pinned':       int(r['pinned'] or 0),
        'views':        int(r['views'] or 0),
        'is_deleted':   0,
        'content_type': r['content_type'] or 'markdown',
        'sort_order':   int(r['sort_order'] or 0),
        'category':     r['category'],
        'created_at':   normalize_ts(r['created_at']),
    })

# 50건씩 배치 삽입
batch_size = 50
total_inserted = 0
for i in range(0, len(posts), batch_size):
    batch = posts[i:i + batch_size]
    res = svc.table('community_posts').insert(batch).execute()
    inserted = len(res.data) if res.data else 0
    total_inserted += inserted
    print(f"  배치 {i // batch_size + 1}: {inserted}건 삽입")

print(f"\n✅ 마이그레이션 완료 — {total_inserted}/{len(posts)}건 Supabase 이전")
