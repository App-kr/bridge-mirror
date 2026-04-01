"""
tools/encrypt_migrate.py
=========================
기존 candidates / client_inquiries 평문 PII 필드를 AES-256-GCM 암호화.

실행:
    python tools/encrypt_migrate.py

조건:
  - BRIDGE_FIELD_KEY 환경변수 필요 (.env에서 자동 로드)
  - 이미 암호화된 값은 건너뜀 (idempotent)
  - 실행 전 자동 백업 생성
"""

import sys, os, sqlite3, hashlib, shutil, datetime
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")

# .env 로드 (없어도 계속)
try:
    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")
except ImportError:
    pass

# BX (DPAPI) 로드 — Windows 로컬 실행 시 BRIDGE_FIELD_KEY 자동 주입
try:
    from tools.bx import load_to_env as _bx_load
    _bx_load()
except Exception:
    pass

from security_vault import t3_encrypt, is_t3_encrypted as is_encrypted

DB_PATH = BASE / "master.db"

# ── 암호화 대상 필드 ─────────────────────────────────────────────────────────
# 검색/이메일 발송에 쓰이는 name/email/phone은 평문 유지
CANDIDATE_FIELDS = [
    # 기존 (v1)
    "dob",
    "nationality",
    "current_location",
    "reference",
    "korean_criminal_record",
    # 추가 (v2) — 검색 대상 아닌 민감 PII
    "kakao_id",
    "passport_number",
    "home_country",
    "emergency_contact",
    "gender",
]

INQUIRY_FIELDS = [
    # 기존 (v1)
    "school_location",
    "memo",
    # 추가 (v2)
    "contact_name",
    "business_registration",
]

def p(msg=""):
    print(msg)

def cv(v):
    if v is None:
        return None
    s = str(v).strip()
    return s if s and s not in ("None", "nan", "") else None


def run_migration():
    # PRE 백업
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = str(DB_PATH) + f".backup_encrypt_migrate_{ts}"
    shutil.copy2(str(DB_PATH), backup_path)
    p(f"백업 생성: {backup_path}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA busy_timeout = 10000")
    cur = conn.cursor()

    # ── 1. candidates ────────────────────────────────────────────────────────
    p()
    p("=== candidates PII 암호화 마이그레이션 ===")

    # 실제 존재하는 컬럼만 필터링
    cur.execute("PRAGMA table_info(candidates)")
    cand_cols = {r[1] for r in cur.fetchall()}
    eff_cand = [f for f in CANDIDATE_FIELDS if f in cand_cols]
    missing = [f for f in CANDIDATE_FIELDS if f not in cand_cols]
    if missing:
        p(f"  [SKIP] DB에 없는 컬럼: {missing}")

    cur.execute("SELECT candidate_id FROM candidates")
    all_ids = [r[0] for r in cur.fetchall()]
    p(f"  대상: {len(all_ids)}건 × {len(eff_cand)}필드")

    cand_stats = {f: {"encrypted": 0, "skipped_empty": 0, "already": 0} for f in eff_cand}

    for cid in all_ids:
        updates = []
        params = []
        for field in eff_cand:
            cur.execute(f"SELECT {field} FROM candidates WHERE candidate_id = ?", (cid,))
            row = cur.fetchone()
            if not row:
                continue
            val = cv(row[0])
            if not val:
                cand_stats[field]["skipped_empty"] += 1
                continue
            if is_encrypted(val):
                cand_stats[field]["already"] += 1
                continue
            enc = t3_encrypt(val, field)
            updates.append(f"{field} = ?")
            params.append(enc)
            cand_stats[field]["encrypted"] += 1
        if updates:
            params.append(cid)
            cur.execute(f"UPDATE candidates SET {', '.join(updates)} WHERE candidate_id = ?", params)

    conn.commit()

    p()
    p("  결과:")
    for field, s in cand_stats.items():
        p(f"    {field:30s}: 신규암호화={s['encrypted']:4d} / 이미암호화={s['already']:4d} / 빈값={s['skipped_empty']:4d}")

    # ── 2. client_inquiries ──────────────────────────────────────────────────
    p()
    p("=== client_inquiries PII 암호화 마이그레이션 ===")

    cur.execute("PRAGMA table_info(client_inquiries)")
    inq_cols = {r[1] for r in cur.fetchall()}
    eff_inq = [f for f in INQUIRY_FIELDS if f in inq_cols]
    missing2 = [f for f in INQUIRY_FIELDS if f not in inq_cols]
    if missing2:
        p(f"  [SKIP] DB에 없는 컬럼: {missing2}")

    cur.execute("SELECT id FROM client_inquiries WHERE is_deleted = 0")
    all_inq_ids = [r[0] for r in cur.fetchall()]
    p(f"  대상: {len(all_inq_ids)}건 × {len(eff_inq)}필드")

    inq_stats = {f: {"encrypted": 0, "skipped_empty": 0, "already": 0} for f in eff_inq}

    for rid in all_inq_ids:
        updates = []
        params = []
        for field in eff_inq:
            cur.execute(f"SELECT {field} FROM client_inquiries WHERE id = ?", (rid,))
            row = cur.fetchone()
            if not row:
                continue
            val = cv(row[0])
            if not val:
                inq_stats[field]["skipped_empty"] += 1
                continue
            if is_encrypted(val):
                inq_stats[field]["already"] += 1
                continue
            enc = t3_encrypt(val, field)
            updates.append(f"{field} = ?")
            params.append(enc)
            inq_stats[field]["encrypted"] += 1
        if updates:
            params.append(rid)
            cur.execute(f"UPDATE client_inquiries SET {', '.join(updates)} WHERE id = ?", params)

    conn.commit()

    p()
    p("  결과:")
    for field, s in inq_stats.items():
        p(f"    {field:30s}: 신규암호화={s['encrypted']:4d} / 이미암호화={s['already']:4d} / 빈값={s['skipped_empty']:4d}")

    # ── 3. POST 검증 ─────────────────────────────────────────────────────────
    p()
    p("=== 검증 ===")
    cur.execute("PRAGMA integrity_check")
    ic = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM candidates")
    c = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM client_inquiries")
    e = cur.fetchone()[0]
    conn.close()

    p(f"  integrity: {ic}")
    p(f"  candidates: {c}건")
    p(f"  client_inquiries: {e}건")

    assert ic == "ok", f"DB 손상! {ic}"
    assert c >= 3000, f"candidates 이상: {c}"

    # 체크섬 기록
    chk = hashlib.sha256(Path(DB_PATH).read_bytes()).hexdigest()
    with open(BASE / "tasks" / "db_checksum.log", "a") as f:
        f.write(f"{datetime.datetime.now().isoformat()} ENCRYPT-MIGRATE {chk}\n")

    p()
    p(f"✅ 마이그레이션 완료. POST 체크섬: {chk[:16]}...")
    p(f"   백업: {backup_path}")


if __name__ == "__main__":
    if not os.getenv("BRIDGE_FIELD_KEY"):
        print("[CRITICAL] BRIDGE_FIELD_KEY 환경변수 없음 — .env 확인 후 재실행")
        sys.exit(1)
    run_migration()
