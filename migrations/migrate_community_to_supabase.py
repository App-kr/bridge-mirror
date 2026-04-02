"""
migrate_community_to_supabase.py
SQLite community_posts → Supabase 초기 시딩 스크립트

사용법:
  # 기본 실행 (이미 시딩된 경우 자동 종료)
  "Q:/Phtyon 3/python.exe" -X utf8 migrations/migrate_community_to_supabase.py

  # 강제 재시딩 (기존 데이터 전체 삭제 후 재삽입 — 주의!)
  "Q:/Phtyon 3/python.exe" -X utf8 migrations/migrate_community_to_supabase.py --force

사전 조건:
  1. supabase.com → SQL Editor → supabase_community_setup.sql 실행 완료
  2. 환경변수 SUPABASE_URL, SUPABASE_SERVICE_KEY 설정
     (service_role 키여야 함 — anon 키 사용 시 자동 거부)

안전 설계:
  - _seed_log 테이블로 중복 실행 추적 → 2회 실행 시 자동 종료
  - service_role 키 JWT 검증 → anon 키 사용 시 즉시 거부
  - --force 없이는 기존 데이터 절대 삭제 안 함
"""
import base64
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── 환경변수 로딩 ─────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

SUPABASE_URL     = os.getenv("SUPABASE_URL", "")
SUPABASE_SVC_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
DB_PATH          = os.getenv("DB_PATH", os.getenv("BRIDGE_DB_PATH",
                   str(Path(__file__).resolve().parent.parent / "master.db")))
FORCE            = "--force" in sys.argv
SEED_ID          = "community_v1"

# ── 1. 입력 검증 ──────────────────────────────────────────────────────────────
if not SUPABASE_URL or not SUPABASE_SVC_KEY:
    print("ERROR: SUPABASE_URL 및 SUPABASE_SERVICE_KEY 환경변수가 필요합니다.")
    sys.exit(1)

# service_role 키 JWT 검증
def _is_service_role_key(key: str) -> bool:
    try:
        parts = key.split('.')
        if len(parts) < 2:
            return False
        padded = parts[1] + '=' * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.b64decode(padded).decode('utf-8'))
        return payload.get('role') == 'service_role'
    except Exception:
        return False

if not _is_service_role_key(SUPABASE_SVC_KEY):
    print("🚨 SECURITY HALT: SUPABASE_SERVICE_KEY가 service_role 키가 아닙니다.")
    print("   Supabase 대시보드 → Settings → API → service_role 키를 사용하세요.")
    print("   anon 키는 RLS로 인해 INSERT/UPDATE/DELETE가 차단됩니다.")
    sys.exit(1)

print(f"[OK] service_role 키 검증 완료")

if not Path(DB_PATH).exists():
    print(f"ERROR: master.db 없음 → {DB_PATH}")
    sys.exit(1)

try:
    from supabase import create_client
except ImportError:
    print("ERROR: pip install supabase")
    sys.exit(1)

svc = create_client(SUPABASE_URL, SUPABASE_SVC_KEY)

# ── 2. 중복 실행 방지: _seed_log 확인 ────────────────────────────────────────
try:
    seed_check = svc.table('_seed_log').select('id,seeded_at,note').eq('id', SEED_ID).execute()
    if seed_check.data and not FORCE:
        rec = seed_check.data[0]
        print(f"\n[SKIP] 이미 시딩 완료됨: id={rec['id']}, seeded_at={rec['seeded_at']}")
        print(f"       note={rec.get('note', '')}")
        print(f"\n       재시딩이 필요하면 --force 플래그를 사용하세요 (기존 데이터 전체 삭제 후 재삽입).")
        sys.exit(0)
    elif seed_check.data and FORCE:
        print(f"\n[FORCE] 기존 시딩 기록 있음. 데이터 초기화 후 재삽입합니다.")
        svc.table('community_posts').delete().neq('id', 0).execute()  # 전체 삭제
        svc.table('boards').delete().neq('id', '').execute()
        svc.table('_seed_log').delete().eq('id', SEED_ID).execute()
        print("  community_posts, boards 초기화 완료.")
except Exception as e:
    print(f"[WARN] _seed_log 확인 실패 (테이블 없을 수 있음): {e}")
    print("       supabase_community_setup.sql을 먼저 실행했는지 확인하세요.")

# ── 3. SQLite 읽기 ────────────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT * FROM community_posts WHERE is_deleted=0 ORDER BY id"
).fetchall()
board_rows = conn.execute("SELECT * FROM boards").fetchall()
conn.close()

print(f"\n[SQLite] community_posts: {len(rows)}건, boards: {len(board_rows)}건")

if not rows:
    print("마이그레이션할 데이터가 없습니다.")
    sys.exit(0)

# ── 4. 타임스탬프 정규화 ──────────────────────────────────────────────────────
def normalize_ts(ts) -> str:
    if not ts:
        return datetime.now(timezone.utc).isoformat()
    ts = str(ts)
    try:
        if 'T' not in ts and '+' not in ts and 'Z' not in ts:
            ts = ts.replace(' ', 'T') + '+00:00'
        return ts
    except Exception:
        return datetime.now(timezone.utc).isoformat()

# ── 5. boards 삽입 ────────────────────────────────────────────────────────────
if board_rows:
    print("\n[boards 삽입]")
    boards_data = [{
        'id': b['id'], 'label': b['label'],
        'label_kr': b['label_kr'],
        'display_mode': b['display_mode'] or 'list',
        'sort_order': int(b['sort_order'] or 0),
        'is_hidden': int(b['is_hidden'] or 0),
    } for b in board_rows]
    try:
        svc.table('boards').upsert(boards_data, on_conflict='id').execute()
        print(f"  {len(boards_data)}개 upsert 완료")
    except Exception as e:
        print(f"  [WARN] boards 삽입 실패: {e}")

# ── 6. community_posts 배치 삽입 ──────────────────────────────────────────────
print("\n[community_posts 삽입]")
posts = []
for r in rows:
    posts.append({
        'board':        r['board'],
        'title':        r['title'] or '',
        'body':         r['body'] or '',
        'author_hash':  r['author_hash'] or '',
        'image_paths':  r['image_paths'] if 'image_paths' in r.keys() else '[]',
        'pinned':       int(r['pinned'] or 0),
        'views':        int(r['views'] or 0),
        'is_deleted':   0,
        'content_type': r['content_type'] or 'markdown',
        'sort_order':   int(r['sort_order'] or 0),
        'category':     r['category'],
        'created_at':   normalize_ts(r['created_at']),
    })

batch_size = 50
total_inserted = 0
for i in range(0, len(posts), batch_size):
    batch = posts[i:i + batch_size]
    res = svc.table('community_posts').insert(batch).execute()
    n = len(res.data) if res.data else 0
    total_inserted += n
    print(f"  배치 {i // batch_size + 1}/{(len(posts) - 1) // batch_size + 1}: {n}건 삽입")

print(f"\n✅ community_posts: {total_inserted}/{len(posts)}건 이전 완료")

# ── 7. _seed_log 기록 (중복 방지 마커) ───────────────────────────────────────
try:
    svc.table('_seed_log').upsert({
        'id': SEED_ID,
        'note': f"SQLite master.db → Supabase, {total_inserted}건, {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
    }, on_conflict='id').execute()
    print(f"[OK] _seed_log 기록 완료 (id={SEED_ID}) — 이후 재실행 시 자동 스킵됨")
except Exception as e:
    print(f"[WARN] _seed_log 기록 실패: {e}")
    print("       수동으로 확인 필요 — 다음 실행 시 중복 삽입될 수 있습니다.")
