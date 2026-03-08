"""
word_import_full.py — ZERO TRUNCATION IMPORT
word_import.csv → master.db jobs 테이블 전체 동기화

정책:
  - 신규 job_code → INSERT (brj_id 자동 생성)
  - 기존 job_code → raw_text / internal_notes / city UPSERT (절대 축소 금지)
  - DB 전용 레코드 → 완전 보존 (삭제/변경 없음)
"""

import re, sqlite3, sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH   = Path("Q:/Claudework/bridge base/master.db")
CSV_PATH  = Path("Q:/Claudework/bridge base/import_source/word_import.csv")

# ── 도시명 패턴 ──────────────────────────────────────────────────────
CITY_PAT = re.compile(
    r'^(Seoul[^,\n]*?|Busan|Incheon|Suwon|Daegu|Daejeon|Gwangju|Ulsan|Sejong|'
    r'Jeju[^,\n]*?|Goyang|Yongin|Seongnam|Bucheon|Ansan|Anyang|Changwon|Jeonju|'
    r'Cheongju|Cheonan|Pohang|Gimpo|Paju|Hanam|Namyangju|Uijeongbu|Hwaseong|'
    r'Pyeongtaek|Gumi|Gunsan|Jinju|Wonju|Chuncheon|Gangwon[^,\n]*?|Gyeongbuk|'
    r'Gyeongnam|Dongtan|Wirye|Gunpo|Uiwang|Gwacheon|Gwangmyeong|Guri|Osan|'
    r'Siheung|Suncheon|Gimhae|Yangsan|Masan|Iksan|Mokpo|Yeosu|Jeonlado|'
    r'Gyeongsang|Boryeong|Chungju|Asan|Eumseong|Geoje|Chungbuk|Chungcheongnam[^,\n]*?|'
    r'Geochang|Gyeongju|Tongyeong|Icheon|Gangwondo|Yangju|Dongducheon|'
    r'Outskirts|Northern|Gyeonggi[^,\n]*?)$',
    re.IGNORECASE
)
JOB_PAT = re.compile(r'^Job\.\s*(\d+)$')

# ── 필드 파서 ────────────────────────────────────────────────────────
FIELD_MAP = {
    'starting date': 'start_date',
    'teaching age': 'teaching_age',
    'class size': 'class_size',
    'working hours': 'working_hours',
    'monthly salary': 'salary_raw',
    'average teaching hours per week': 'teach_hrs_week',
    'vacation': 'vacation',
    'native teacher': 'native_count',
    'housing': 'housing',
    'employee benefits': 'benefits',
}

def parse_fields(raw: str) -> dict:
    out = {}
    for line in raw.splitlines():
        line = line.lstrip('`').lstrip('"').rstrip('"').strip()
        for key, col in FIELD_MAP.items():
            if line.lower().startswith(key):
                val = re.sub(rf'^{re.escape(key)}\s*[:\-]?\s*', '', line, flags=re.IGNORECASE).strip()
                if val:
                    out[col] = val[:500]
                break
    return out

# ── 도시 → region 매핑 ────────────────────────────────────────────────
REGION_MAP = {
    'Seoul': ('SE', '서울'), 'Busan': ('BS', '부산'), 'Incheon': ('IC', '인천'),
    'Suwon': ('GG', '경기'), 'Seongnam': ('GG', '경기'), 'Yongin': ('GG', '경기'),
    'Goyang': ('GG', '경기'), 'Bucheon': ('GG', '경기'), 'Ansan': ('GG', '경기'),
    'Anyang': ('GG', '경기'), 'Gimpo': ('GG', '경기'), 'Paju': ('GG', '경기'),
    'Hanam': ('GG', '경기'), 'Namyangju': ('GG', '경기'), 'Uijeongbu': ('GG', '경기'),
    'Hwaseong': ('GG', '경기'), 'Pyeongtaek': ('GG', '경기'), 'Dongtan': ('GG', '경기'),
    'Wirye': ('GG', '경기'), 'Gunpo': ('GG', '경기'), 'Uiwang': ('GG', '경기'),
    'Gwacheon': ('GG', '경기'), 'Gwangmyeong': ('GG', '경기'), 'Guri': ('GG', '경기'),
    'Osan': ('GG', '경기'), 'Siheung': ('GG', '경기'), 'Yangju': ('GG', '경기'),
    'Dongducheon': ('GG', '경기'), 'Icheon': ('GG', '경기'),
    'Daegu': ('DG', '대구'), 'Daejeon': ('DJ', '대전'), 'Gwangju': ('GJ', '광주'),
    'Ulsan': ('US', '울산'), 'Sejong': ('SJ', '세종'),
    'Jeju': ('JJ', '제주'), 'Changwon': ('GN', '경남'), 'Jeonju': ('JB', '전북'),
    'Cheongju': ('CB', '충북'), 'Cheonan': ('CN', '충남'), 'Pohang': ('GB', '경북'),
    'Gumi': ('GB', '경북'), 'Jinju': ('GN', '경남'), 'Wonju': ('GW', '강원'),
    'Chuncheon': ('GW', '강원'), 'Suncheon': ('JN', '전남'), 'Gimhae': ('GN', '경남'),
    'Yangsan': ('GN', '경남'), 'Masan': ('GN', '경남'), 'Iksan': ('JB', '전북'),
    'Mokpo': ('JN', '전남'), 'Yeosu': ('JN', '전남'), 'Boryeong': ('CN', '충남'),
    'Chungju': ('CB', '충북'), 'Asan': ('CN', '충남'), 'Eumseong': ('CB', '충북'),
    'Geoje': ('GN', '경남'), 'Geochang': ('GN', '경남'), 'Gyeongju': ('GB', '경북'),
    'Tongyeong': ('GN', '경남'), 'Gangwondo': ('GW', '강원'), 'Gunsan': ('JB', '전북'),
}

def city_to_region(city: str):
    if not city:
        return ('ETC', '기타')
    for key, val in REGION_MAP.items():
        if city.lower().startswith(key.lower()):
            return val
    return ('ETC', '기타')

def make_brj_id(city: str, region_code: str, seq: int) -> str:
    now = datetime.now(timezone.utc)
    ym = now.strftime('%y%m')
    c = city[:2].upper() if city else 'XX'
    return f"BRJ-{region_code}-{ym}-W{seq:03d}"

# ── CSV 파서 ─────────────────────────────────────────────────────────
def parse_csv(path: Path) -> list[dict]:
    with open(path, 'r', encoding='utf-8-sig') as f:
        lines = f.read().split('\n')

    jobs = []
    i = 0
    pending_city = None
    pending_note = None

    while i < len(lines):
        raw_line = lines[i]
        stripped = raw_line.strip().strip('"')

        jm = JOB_PAT.match(stripped)
        if jm:
            num = jm.group(1)
            job_code = f"Job.{num}"

            # Collect body lines until next job or EOF
            body_lines = [stripped]
            i += 1
            employer_footer = None
            next_city = None

            while i < len(lines):
                l = lines[i].strip()
                # Next job starts?
                if JOB_PAT.match(l.strip('"')):
                    break
                # Korean employer note (footer of this job / header of next)
                if (l.startswith('(') or l.startswith('"(')) and len(l) > 5:
                    employer_footer = l
                    body_lines.append(l)
                    i += 1
                    continue
                # City line → belongs to NEXT job
                if CITY_PAT.match(l) and l:
                    next_city = l
                    i += 1
                    break
                body_lines.append(l)
                i += 1

            raw_text = '\n'.join(body_lines).strip()
            fields = parse_fields(raw_text)
            region_code, region_name = city_to_region(pending_city)

            jobs.append({
                'job_code': job_code,
                'city': pending_city,
                'region': region_code,
                'region_name': region_name,
                'internal_notes': (pending_note or '').strip('"').strip(),
                'raw_text': raw_text,
                'raw_source': 'word_import.csv',
                **fields,
            })

            pending_city = next_city
            pending_note = None
            continue

        # Korean employer note (header before job)
        if (stripped.startswith('(') or stripped.startswith('"(')) and len(stripped) > 3:
            pending_note = stripped
            i += 1
            continue

        # City line
        if CITY_PAT.match(stripped) and stripped:
            pending_city = stripped
            i += 1
            continue

        i += 1

    return jobs

# ── 메인 임포트 ──────────────────────────────────────────────────────
def run():
    print("=" * 60)
    print("WORD IMPORT - ZERO TRUNCATION POLICY")
    print("=" * 60)

    jobs = parse_csv(CSV_PATH)
    print(f"CSV 파싱: {len(jobs)}건")

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 기존 DB 상태
    cur.execute("SELECT job_code, raw_text, city FROM jobs WHERE is_deleted=0")
    db_map = {r['job_code']: dict(r) for r in cur.fetchall()}
    print(f"DB 기존: {len(db_map)}건")

    # 신규 brj_id 시퀀스 (W prefix = Word import)
    cur.execute("SELECT MAX(id) FROM jobs")
    max_id = cur.fetchone()[0] or 0

    now_iso = datetime.now(timezone.utc).isoformat()
    inserted = 0
    updated  = 0
    skipped  = 0

    for idx, job in enumerate(jobs):
        code = job['job_code']

        if code not in db_map:
            # ── INSERT 신규 ──
            region_code = job.get('region', 'ETC')
            brj_id = make_brj_id(job.get('city', ''), region_code, inserted + 1)
            cur.execute("""
                INSERT INTO jobs (
                    job_code, brj_id, city, region, region_name,
                    internal_notes, raw_text, raw_source,
                    start_date, teaching_age, class_size,
                    working_hours, salary_raw, teach_hrs_week,
                    vacation, native_count, housing, benefits,
                    status, is_hot, is_deleted,
                    loaded_at, created_at
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    'open', 0, 0,
                    ?, ?
                )
            """, (
                code,
                brj_id,
                job.get('city') or '',
                job.get('region') or 'ETC',
                job.get('region_name') or '기타',
                job.get('internal_notes') or '',
                job.get('raw_text') or '',
                'word_import.csv',
                job.get('start_date'),
                job.get('teaching_age'),
                job.get('class_size'),
                job.get('working_hours'),
                job.get('salary_raw'),
                job.get('teach_hrs_week'),
                job.get('vacation'),
                job.get('native_count'),
                job.get('housing'),
                job.get('benefits'),
                now_iso,
                now_iso,
            ))
            inserted += 1

        else:
            # ── UPDATE: raw_text ZERO TRUNCATION ──
            existing_raw  = db_map[code].get('raw_text') or ''
            new_raw       = job.get('raw_text') or ''
            existing_city = db_map[code].get('city') or ''
            new_city      = job.get('city') or ''
            new_notes     = job.get('internal_notes') or ''

            # Only update if new content is longer or city/notes need filling
            needs_update = (
                len(new_raw) > len(existing_raw) or
                (not existing_city and new_city) or
                new_notes
            )

            if needs_update:
                # Merge: keep longer raw_text
                merged_raw = new_raw if len(new_raw) >= len(existing_raw) else existing_raw
                cur.execute("""
                    UPDATE jobs
                    SET raw_text       = ?,
                        city           = CASE WHEN (city IS NULL OR city='') THEN ? ELSE city END,
                        internal_notes = CASE WHEN (internal_notes IS NULL OR internal_notes='') THEN ? ELSE internal_notes END
                    WHERE job_code = ? AND is_deleted = 0
                """, (
                    merged_raw,
                    new_city,
                    new_notes,
                    code,
                ))
                updated += 1
            else:
                skipped += 1

    conn.commit()

    # 최종 검증
    cur.execute("SELECT COUNT(*) FROM jobs WHERE is_deleted=0")
    final_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM jobs WHERE is_deleted=0 AND (raw_text IS NOT NULL AND raw_text != '')")
    has_raw = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM jobs WHERE raw_source='word_import.csv'")
    word_source = cur.fetchone()[0]

    conn.close()

    print()
    print("=" * 60)
    print("임포트 완료 - ZERO TRUNCATION")
    print("=" * 60)
    print(f"  신규 INSERT  : {inserted}건")
    print(f"  raw_text 갱신: {updated}건")
    print(f"  변경 없음    : {skipped}건")
    print(f"  DB 최종 총계 : {final_total}건")
    print(f"  raw_text 보유: {has_raw}건")
    print(f"  word 소스    : {word_source}건")
    print("=" * 60)

if __name__ == "__main__":
    run()
