"""
migrate_inquiry_to_jobs.py — client_inquiries → jobs 일괄 마이그레이션
실행: python tools/migrate_inquiry_to_jobs.py [--dry-run]
"""
import sqlite3
import re
import sys
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
_log = logging.getLogger("migrate")

DB_PATH = "Q:/Claudework/bridge base/master.db"
DRY_RUN = "--dry-run" in sys.argv

def _parse_salary(salary_raw: str):
    nums = re.findall(r"[\d]+", (salary_raw or "").replace(",", ""))
    salary_min = float(nums[0]) if nums else None
    salary_max = float(nums[-1]) if len(nums) > 1 else salary_min
    return salary_min, salary_max

def _parse_daily_hours(wh: str):
    m = re.search(r"(\d{1,2}):?(\d{2})\s*[~\-]\s*(\d{1,2}):?(\d{2})", wh or "")
    if m:
        h1 = int(m.group(1)) + int(m.group(2)) / 60
        h2 = int(m.group(3)) + int(m.group(4)) / 60
        return round(h2 - h1, 2) if h2 > h1 else None
    return None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row

    # 1. inquiry_id 컬럼 추가 (없으면)
    existing_cols = [r[1] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()]
    if "inquiry_id" not in existing_cols:
        _log.info("ALTER TABLE jobs ADD COLUMN inquiry_id INTEGER")
        if not DRY_RUN:
            conn.execute("ALTER TABLE jobs ADD COLUMN inquiry_id INTEGER")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_inquiry_id ON jobs(inquiry_id)")
            conn.commit()
    else:
        _log.info("inquiry_id 컬럼 이미 존재")

    # 2. 이미 이전된 inquiry_id 목록 조회
    if "inquiry_id" in existing_cols or not DRY_RUN:
        existing_inquiry_ids = set(
            r[0] for r in conn.execute(
                "SELECT inquiry_id FROM jobs WHERE inquiry_id IS NOT NULL"
            ).fetchall()
        )
    else:
        existing_inquiry_ids = set()

    # 3. 이전할 client_inquiries 조회
    rows = conn.execute(
        "SELECT * FROM client_inquiries WHERE is_deleted = 0 ORDER BY id"
    ).fetchall()
    _log.info("이전 대상 client_inquiries: %d건", len(rows))

    inserted = 0
    skipped = 0
    errors = 0

    for inq in rows:
        inq_id = inq["id"]
        school_name = inq["school_name"] or ""

        # 중복 체크: inquiry_id 기준
        if inq_id in existing_inquiry_ids:
            skipped += 1
            continue

        # notes에 JOB_REGISTERED 있어도 skip
        notes_val = inq["notes"] or ""
        if "JOB_REGISTERED" in notes_val:
            skipped += 1
            continue

        try:
            salary_raw = inq["salary_raw"] or ""
            salary_min, salary_max = _parse_salary(salary_raw)
            wh = inq["working_hours"] or inq["schedule"] or ""
            daily_hours = _parse_daily_hours(wh)

            loc = inq["location"] or ""
            city = loc.split(",")[0].split(" ")[0].strip() if loc else ""

            housing_val = inq["housing_detail"] or inq["housing_type"] or ""
            memo_raw = inq["memo"] or ""

            contact_name = inq["contact_name"] or ""
            phone_val = inq["phone"] or ""
            email_val = inq["email"] or ""

            internal_notes = memo_raw
            if not internal_notes and (contact_name or school_name):
                internal_notes = f"{school_name} / {contact_name} / {phone_val} / {email_val}"

            # raw_text 요약
            raw_parts = [f"School: {school_name}", f"Location: {loc}"]
            if inq["start_date"]:   raw_parts.append(f"Starting Date : {inq['start_date']}")
            if inq["teaching_age"]: raw_parts.append(f"Teaching Age : {inq['teaching_age']}")
            if salary_raw:          raw_parts.append(f"Salary : {salary_raw}")
            if wh:                  raw_parts.append(f"Working Hours : {wh}")
            if housing_val:         raw_parts.append(f"Housing : {housing_val}")
            if inq["benefits"]:     raw_parts.append(f"Benefits : {inq['benefits']}")
            raw_text = "\n".join(raw_parts)

            submitted_at = inq["submitted_at"] or datetime.now(timezone.utc).isoformat()
            job_code = f"WEB-{inq_id}"

            if DRY_RUN:
                _log.info("[DRY] INSERT jobs: inquiry_id=%d job_code=%s school=%s",
                          inq_id, job_code, school_name[:40])
                inserted += 1
                continue

            cur = conn.execute(
                """INSERT OR IGNORE INTO jobs
                   (seq, job_code, location, city, start_date, teaching_age,
                    working_hours, daily_hours, salary_min, salary_max, salary_raw,
                    vacation, housing, housing_type, housing_detail,
                    benefits, status, is_hot, is_deleted, created_at,
                    internal_notes, raw_text, employer_display_name,
                    source_file, inquiry_id)
                   VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_review',
                           0, 0, ?, ?, ?, ?, 'web_form', ?)""",
                (
                    job_code, loc, city, inq["start_date"], inq["teaching_age"],
                    wh, daily_hours, salary_min, salary_max, salary_raw,
                    inq["vacation"], housing_val, inq["housing_type"], inq["housing_detail"],
                    inq["benefits"], submitted_at,
                    internal_notes, raw_text, school_name, inq_id,
                ),
            )
            if cur.rowcount > 0:
                new_job_id = cur.lastrowid
                # client_inquiries.notes에 JOB_REGISTERED 마커 기록
                new_notes = f"{notes_val}\nJOB_REGISTERED:{job_code}".strip()
                conn.execute(
                    "UPDATE client_inquiries SET notes = ? WHERE id = ?",
                    (new_notes, inq_id)
                )
                inserted += 1
                existing_inquiry_ids.add(inq_id)
            else:
                skipped += 1

        except Exception as e:
            _log.error("inquiry_id=%d 처리 실패: %s", inq_id, e)
            errors += 1

    if not DRY_RUN:
        conn.commit()

    conn.close()

    _log.info("완료 — INSERT: %d, SKIP: %d, ERROR: %d (DRY_RUN=%s)",
              inserted, skipped, errors, DRY_RUN)
    print(f"\n결과: {inserted}건 이전 완료, {skipped}건 건너뜀, {errors}건 오류")

if __name__ == "__main__":
    main()
