"""
jobs 테이블 v2 마이그레이션: BRJ ID 체계 + 확장 컬럼
기존 데이터 100% 보존, ALTER TABLE ADD COLUMN 방식
"""
import sqlite3
import sys
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "master.db")

REGION_CODES = {
    "Seoul": "SE", "서울": "SE",
    "Busan": "BS", "부산": "BS",
    "Daegu": "DG", "대구": "DG",
    "Incheon": "IC", "인천": "IC",
    "Gwangju": "GJ", "광주": "GJ",
    "Daejeon": "DJ", "대전": "DJ",
    "Ulsan": "US", "울산": "US",
    "Sejong": "SJ", "세종": "SJ",
    "Gyeonggi": "GG", "경기": "GG",
    "Gangwon": "GW", "강원": "GW",
    "Chungbuk": "CB", "충북": "CB",
    "Chungnam": "CN", "충남": "CN",
    "Jeonbuk": "JB", "전북": "JB",
    "Jeonnam": "JN", "전남": "JN",
    "Gyeongbuk": "KB", "경북": "KB",
    "Gyeongnam": "KN", "경남": "KN",
    "Jeju": "JJ", "제주": "JJ",
    # Common city → region
    "Suwon": "GG", "수원": "GG",
    "Seongnam": "GG", "성남": "GG",
    "Yongin": "GG", "용인": "GG",
    "Goyang": "GG", "고양": "GG",
    "Bucheon": "GG", "부천": "GG",
    "Anyang": "GG", "안양": "GG",
    "Hwaseong": "GG", "화성": "GG",
    "Pyeongtaek": "GG", "평택": "GG",
    "Cheonan": "CN", "천안": "CN",
    "Cheongju": "CB", "청주": "CB",
    "Jeonju": "JB", "전주": "JB",
    "Pohang": "KB", "포항": "KB",
    "Changwon": "KN", "창원": "KN",
    "Gimhae": "KN", "김해": "KN",
    "Jinju": "KN", "진주": "KN",
}

NEW_COLUMNS = [
    ("brj_id", "TEXT"),
    ("legacy_id", "TEXT"),
    ("region", "TEXT"),
    ("region_name", "TEXT"),
    ("enc_employer_name", "TEXT"),
    ("enc_contact_name", "TEXT"),
    ("enc_contact_phone", "TEXT"),
    ("enc_contact_email", "TEXT"),
    ("enc_contact_kakao", "TEXT"),
    ("employer_display_name", "TEXT"),
    ("salary_krw", "INTEGER"),
    ("salary_negotiable", "INTEGER DEFAULT 0"),
    ("housing_type", "TEXT"),
    ("housing_detail", "TEXT"),
    ("vacation_days", "INTEGER"),
    ("visa_sponsorship", "INTEGER DEFAULT 1"),
    ("f_visa_welcome", "INTEGER DEFAULT 0"),
    ("kyopo_welcome", "INTEGER DEFAULT 0"),
    ("degree_requirement", "TEXT"),
    ("korea_resident_only", "INTEGER DEFAULT 0"),
    ("raw_text", "TEXT"),
    ("raw_source", "TEXT"),
    ("teaching_hours_weekly", "TEXT"),
    ("parse_confidence", "REAL DEFAULT 0"),
    ("parse_warnings", "TEXT"),
]


def get_region_code(location_str: str) -> str:
    if not location_str:
        return "XX"
    for key, code in REGION_CODES.items():
        if key.lower() in location_str.lower():
            return code
    return "XX"


def get_region_name(code: str) -> str:
    code_to_name = {
        "SE": "서울", "BS": "부산", "DG": "대구", "IC": "인천",
        "GJ": "광주", "DJ": "대전", "US": "울산", "SJ": "세종",
        "GG": "경기", "GW": "강원", "CB": "충북", "CN": "충남",
        "JB": "전북", "JN": "전남", "KB": "경북", "KN": "경남",
        "JJ": "제주", "XX": "기타",
    }
    return code_to_name.get(code, "기타")


def migrate():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row

    existing = {r[1] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()}

    added = 0
    for col_name, col_type in NEW_COLUMNS:
        if col_name not in existing:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}")
            added += 1
            print(f"  + {col_name} ({col_type})")

    # job_id_migration 테이블
    conn.execute("""
        CREATE TABLE IF NOT EXISTS job_id_migration (
            legacy_id TEXT NOT NULL,
            brj_id TEXT NOT NULL PRIMARY KEY,
            migrated_at TEXT NOT NULL
        )
    """)

    # Assign BRJ IDs to existing rows
    rows = conn.execute("SELECT id, job_code, location, city, created_at, brj_id FROM jobs WHERE is_deleted = 0").fetchall()
    now = datetime.now(timezone.utc).isoformat()

    # Group by region+month for seq numbering
    seq_counters: dict[str, int] = {}
    assigned = 0

    for row in rows:
        if row["brj_id"]:
            continue
        loc = row["location"] or row["city"] or ""
        region_code = get_region_code(loc)
        region_name = get_region_name(region_code)

        created = row["created_at"] or now
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            dt = datetime.now(timezone.utc)
        yymm = dt.strftime("%y%m")
        key = f"{region_code}-{yymm}"
        seq_counters[key] = seq_counters.get(key, 0) + 1
        brj_id = f"BRJ-{region_code}-{yymm}-{seq_counters[key]:03d}"

        legacy_id = row["job_code"] or f"legacy_{row['id']}"

        conn.execute(
            "UPDATE jobs SET brj_id=?, legacy_id=?, region=?, region_name=?, raw_source=? WHERE id=?",
            (brj_id, legacy_id, region_code, region_name, "BRIDGE_clients_jobs.txt", row["id"]),
        )
        conn.execute(
            "INSERT OR IGNORE INTO job_id_migration (legacy_id, brj_id, migrated_at) VALUES (?, ?, ?)",
            (legacy_id, brj_id, now),
        )
        assigned += 1

    conn.commit()
    conn.close()
    print(f"\nMigration done: {added} columns added, {assigned} BRJ IDs assigned.")


if __name__ == "__main__":
    migrate()
