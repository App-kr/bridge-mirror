"""
migrate_admin_tables_to_supabase.py
SQLite 7개 관리자 테이블 → Supabase 1회성 마이그레이션

실행:
  cd "Q:\\Claudework\\bridge base"
  python migrations/migrate_admin_tables_to_supabase.py

사전 조건:
  1. Supabase Dashboard SQL Editor에서 migrations/supabase_admin_tables.sql 먼저 실행
  2. .env에 SUPABASE_URL, SUPABASE_SERVICE_KEY 설정
"""
import os, sys, sqlite3
from pathlib import Path
from datetime import datetime, timezone

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

svc  = create_client(SUPABASE_URL, SUPABASE_SVC_KEY)
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def normalize_ts(ts):
    if not ts:
        return now_iso()
    try:
        if 'T' not in str(ts) and '+' not in str(ts) and 'Z' not in str(ts):
            return str(ts).replace(' ', 'T') + '+00:00'
        return str(ts)
    except Exception:
        return now_iso()


def check_existing(table: str) -> int:
    res = svc.table(table).select('id', count='exact').execute()
    return res.count or 0


def confirm_if_exists(table: str) -> bool:
    cnt = check_existing(table)
    if cnt > 0:
        print(f"  ⚠️  Supabase '{table}'에 이미 {cnt}건 존재합니다.")
        ans = input(f"     계속 진행하면 중복 데이터가 생깁니다. 진행? (yes/no): ").strip()
        return ans.lower() == 'yes'
    return True


def batch_insert(table: str, rows: list, batch_size: int = 50) -> int:
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        res = svc.table(table).insert(batch).execute()
        total += len(res.data) if res.data else 0
        print(f"    배치 {i // batch_size + 1}: {len(res.data) if res.data else 0}건")
    return total


def has_table(table: str) -> bool:
    try:
        conn.execute(f"SELECT 1 FROM {table} LIMIT 1")
        return True
    except sqlite3.OperationalError:
        return False


# ── 1. email_templates ─────────────────────────────────────────
print("\n[1/7] email_templates")
if has_table('email_templates'):
    rows = conn.execute("SELECT template_key, subject, body_html, updated_at FROM email_templates").fetchall()
    print(f"  SQLite: {len(rows)}건")
    if rows and confirm_if_exists('email_templates'):
        data = [{'template_key': r['template_key'], 'subject': r['subject'] or '',
                 'body_html': r['body_html'] or '', 'updated_at': normalize_ts(r['updated_at'])} for r in rows]
        n = batch_insert('email_templates', data)
        print(f"  ✅ {n}/{len(rows)}건 완료")
else:
    print("  SQLite에 email_templates 테이블 없음 — 건너뜀")

# ── 2. guide_links ─────────────────────────────────────────────
print("\n[2/7] guide_links")
if has_table('guide_links'):
    rows = conn.execute("SELECT link_key, url, label, updated_at FROM guide_links").fetchall()
    print(f"  SQLite: {len(rows)}건")
    if rows and confirm_if_exists('guide_links'):
        data = [{'link_key': r['link_key'], 'url': r['url'] or '',
                 'label': r['label'], 'updated_at': normalize_ts(r['updated_at'])} for r in rows]
        n = batch_insert('guide_links', data)
        print(f"  ✅ {n}/{len(rows)}건 완료")
else:
    print("  SQLite에 guide_links 테이블 없음 — 건너뜀")

# ── 3. boards ──────────────────────────────────────────────────
print("\n[3/7] boards")
if has_table('boards'):
    rows = conn.execute("SELECT slug, label, is_visible, sort_order, created_at FROM boards").fetchall()
    print(f"  SQLite: {len(rows)}건")
    if rows and confirm_if_exists('boards'):
        data = [{'slug': r['slug'], 'label': r['label'] or '', 'is_visible': int(r['is_visible'] or 1),
                 'sort_order': int(r['sort_order'] or 0), 'created_at': normalize_ts(r['created_at'])} for r in rows]
        n = batch_insert('boards', data)
        print(f"  ✅ {n}/{len(rows)}건 완료")
else:
    print("  SQLite에 boards 테이블 없음 — 건너뜀")

# ── 4. banners ─────────────────────────────────────────────────
print("\n[4/7] banners")
if has_table('banners'):
    rows = conn.execute("SELECT title, body, link_url, is_active, sort_order, created_at FROM banners").fetchall()
    print(f"  SQLite: {len(rows)}건")
    if rows and confirm_if_exists('banners'):
        data = [{'title': r['title'] or '', 'body': r['body'] or '', 'link_url': r['link_url'],
                 'is_active': int(r['is_active'] or 1), 'sort_order': int(r['sort_order'] or 0),
                 'created_at': normalize_ts(r['created_at'])} for r in rows]
        n = batch_insert('banners', data)
        print(f"  ✅ {n}/{len(rows)}건 완료")
else:
    print("  SQLite에 banners 테이블 없음 — 건너뜀")

# ── 5. site_partners ───────────────────────────────────────────
print("\n[5/7] site_partners")
if has_table('site_partners'):
    rows = conn.execute(
        "SELECT name, category, logo_url, website, is_active, is_deleted, sort_order, created_at FROM site_partners"
    ).fetchall()
    print(f"  SQLite: {len(rows)}건")
    if rows and confirm_if_exists('site_partners'):
        data = [{'name': r['name'] or '', 'category': r['category'], 'logo_url': r['logo_url'],
                 'website': r['website'], 'is_active': int(r['is_active'] or 1),
                 'is_deleted': int(r['is_deleted'] or 0), 'sort_order': int(r['sort_order'] or 0),
                 'created_at': normalize_ts(r['created_at'])} for r in rows]
        n = batch_insert('site_partners', data)
        print(f"  ✅ {n}/{len(rows)}건 완료")
else:
    print("  SQLite에 site_partners 테이블 없음 — 건너뜀")

# ── 6. site_settings ───────────────────────────────────────────
print("\n[6/7] site_settings")
if has_table('site_settings'):
    rows = conn.execute("SELECT key, value, updated_at FROM site_settings").fetchall()
    print(f"  SQLite: {len(rows)}건")
    if rows and confirm_if_exists('site_settings'):
        data = [{'key': r['key'], 'value': r['value'] or '', 'updated_at': normalize_ts(r['updated_at'])} for r in rows]
        n = batch_insert('site_settings', data)
        print(f"  ✅ {n}/{len(rows)}건 완료")
else:
    print("  SQLite에 site_settings 테이블 없음 — 건너뜀")

# ── 7. testimonials ────────────────────────────────────────────
print("\n[7/7] testimonials")
if has_table('testimonials'):
    rows = conn.execute(
        "SELECT name, country, photo_url, rating, review_text, is_visible, is_deleted, sort_order, created_at "
        "FROM testimonials WHERE is_deleted=0"
    ).fetchall()
    print(f"  SQLite: {len(rows)}건")
    if rows and confirm_if_exists('testimonials'):
        data = [{'name': r['name'] or '', 'country': r['country'], 'photo_url': r['photo_url'],
                 'rating': int(r['rating'] or 5), 'review_text': r['review_text'] or '',
                 'is_visible': int(r['is_visible'] or 1), 'is_deleted': 0,
                 'sort_order': int(r['sort_order'] or 0), 'created_at': normalize_ts(r['created_at'])} for r in rows]
        n = batch_insert('testimonials', data)
        print(f"  ✅ {n}/{len(rows)}건 완료")
else:
    print("  SQLite에 testimonials 테이블 없음 — 건너뜀")

conn.close()
print("\n✅ 7개 테이블 마이그레이션 완료")
