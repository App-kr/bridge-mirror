"""
extract_employers.py — BRIDGE_clients_jobs.txt 내부 메모에서 고용주 정보 추출
→ client_inquiries 테이블에 삽입 (source_file='memo_extract')

실행:
  python extract_employers.py            # DB에 삽입
  python extract_employers.py --dry-run  # 파싱 결과만 미리보기
"""

import argparse
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
JOBS_TXT = BASE_DIR / "original_jobs" / "BRIDGE_clients_jobs.txt"
DB_PATH  = BASE_DIR / "master.db"
NOW_ISO  = datetime.now(timezone.utc).isoformat()
SOURCE   = "memo_extract"

# ── 전화번호 패턴 ──
PHONE_RE = re.compile(r'0\d{1,2}[\s\-]?\d{3,4}[\s\-]?\d{3,4}')

# ── 이메일 패턴 ──
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

# ── 직책 키워드 → 담당자명 추출 ──
TITLE_RE = re.compile(
    r'([가-힣]{2,4})\s*(원장|대표|부장|이사|실장|부원장|매니저|관리자|선생|팀장|과장|차장|사장|담당)',
)
# 역순: 직책 + 이름
TITLE_REV_RE = re.compile(
    r'(원장|대표|부장|이사|실장|부원장|매니저|관리자|선생|팀장|과장|차장|사장|담당)\s*([가-힣]{2,4})',
)

# ── 한국 도시 키워드 (메모 시작 부분에서 위치 추출) ──
CITY_KEYWORDS = [
    '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
    '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주',
    '수원', '성남', '고양', '용인', '안양', '안산', '화성', '평택',
    '시흥', '파주', '김포', '광명', '하남', '이천', '양주', '오산',
    '의왕', '군포', '과천', '양평', '여주', '포천', '동두천', '가평',
    '연천', '의정부', '구리', '남양주',
    '춘천', '원주', '강릉', '속초', '동해', '태백', '삼척',
    '청주', '충주', '제천', '천안', '아산', '논산', '공주', '서산', '당진', '보령', '홍성',
    '전주', '군산', '익산', '정읍', '남원', '김제',
    '목포', '여수', '순천', '나주', '광양',
    '포항', '경주', '김천', '안동', '구미', '영주', '상주', '영천', '문경',
    '창원', '진주', '통영', '사천', '김해', '밀양', '거제', '양산',
]


def parse_memo(memo: str, job_code: str, location: str) -> dict | None:
    """메모 문자열에서 고용주 정보를 추출"""
    if not memo or len(memo) < 5:
        return None

    # 괄호 제거
    text = memo.strip()
    if text.startswith('('):
        text = text[1:]
    if text.endswith(')'):
        text = text[:-1]
    text = text.strip()

    if not text:
        return None

    # 1. 전화번호 추출
    phones = PHONE_RE.findall(text)
    phone_str = ' / '.join(phones[:3]) if phones else ''

    # 2. 이메일 추출
    emails = EMAIL_RE.findall(text)
    email_str = ', '.join(emails[:3]) if emails else ''

    # 3. 담당자명 추출
    contact_name = ''
    m = TITLE_RE.search(text)
    if m:
        contact_name = f'{m.group(1)} {m.group(2)}'
    else:
        m2 = TITLE_REV_RE.search(text)
        if m2:
            contact_name = f'{m2.group(2)} {m2.group(1)}'

    # 4. 학원/학교명 추출 (위치 키워드 뒤, 전화번호/이메일 앞)
    school_name = ''
    # 위치 키워드 제거 후 남은 앞부분에서 학원명 추출
    remaining = text
    for city in CITY_KEYWORDS:
        if remaining.startswith(city):
            remaining = remaining[len(city):].strip()
            break

    # 구/동/읍 이름 제거 (2-4글자 한글)
    district_match = re.match(r'^([가-힣]{1,5})\s+', remaining)
    if district_match:
        remaining = remaining[district_match.end():].strip()

    # 첫 번째 전화번호나 이메일까지의 텍스트에서 학원명 추출
    first_phone_pos = len(remaining)
    for p in phones:
        pos = remaining.find(p)
        if pos >= 0 and pos < first_phone_pos:
            first_phone_pos = pos
    for e in emails:
        pos = remaining.find(e)
        if pos >= 0 and pos < first_phone_pos:
            first_phone_pos = pos

    name_part = remaining[:first_phone_pos].strip()
    # 직책/이름 키워드 앞까지
    title_pos = len(name_part)
    for title_word in ['원장', '대표', '부장', '이사', '실장', '부원장', '매니저', '담당', '팀장']:
        pos = name_part.find(title_word)
        if pos >= 0 and pos < title_pos:
            # 직책 키워드 앞 이름(2-4글자) 제외
            check_pos = max(0, pos - 4)
            title_pos = check_pos if check_pos > 0 else pos

    school_candidate = name_part[:title_pos].strip()
    # 마지막 2-3글자 한글 이름 제거 (담당자 이름일 가능성)
    name_suffix = re.search(r'\s+([가-힣]{2,3})$', school_candidate)
    if name_suffix and not contact_name:
        contact_name = name_suffix.group(1)
        school_candidate = school_candidate[:name_suffix.start()].strip()

    if school_candidate and len(school_candidate) >= 2:
        school_name = school_candidate
    else:
        school_name = name_part.strip()[:40] if name_part else ''

    # 5. 위치 — 메모 앞부분 or job location
    memo_location = ''
    for city in CITY_KEYWORDS:
        if text.startswith(city) or f' {city}' in text[:20]:
            idx = text.find(city)
            loc_end = text.find(' ', idx + len(city) + 1)
            if loc_end < 0 or loc_end > idx + 15:
                loc_end = idx + len(city) + 5
            memo_location = text[idx:loc_end].strip()
            break
    if not memo_location:
        memo_location = location or ''

    # 6. 메모 전체 텍스트 (원본 보존)
    return {
        'school_name':  school_name[:100] if school_name else f'({job_code} 메모)',
        'contact_name': contact_name[:50],
        'phone':        phone_str[:100],
        'email':        email_str[:200],
        'location':     memo_location[:100],
        'memo':         memo[:500],
        'source_file':  SOURCE,
        'loaded_at':    NOW_ISO,
        'submitted_at': None,
        'vacancies':    None,
        'teaching_age': None,
        'schedule':     None,
        'working_hours': None,
        'salary_raw':   None,
        'housing_type': None,
        'housing_detail': None,
        'travel_support': None,
        'benefits':     None,
        'vacation':     None,
        'sick_leave':   None,
        'meal':         None,
        'start_date':   None,
    }


def parse_all_memos(db_path: Path) -> list[dict]:
    """jobs 테이블에서 internal_notes를 읽어 파싱"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        'SELECT job_code, internal_notes, location FROM jobs '
        'WHERE internal_notes IS NOT NULL AND internal_notes != "" '
        'ORDER BY id'
    ).fetchall()
    conn.close()

    results = []
    seen_notes = set()
    for row in rows:
        notes = row['internal_notes'].strip()
        if notes in seen_notes:
            continue
        seen_notes.add(notes)

        # 괄호로 구분된 여러 메모가 하나의 notes에 있을 수 있음
        # 예: (학원A 010...) (학원B 010...)
        # 개별 괄호 단위로 분리
        memo_parts = []
        if notes.count('(') > 1:
            # 다중 괄호 분리
            depth = 0
            start = -1
            for i, ch in enumerate(notes):
                if ch == '(':
                    if depth == 0:
                        start = i
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0 and start >= 0:
                        memo_parts.append(notes[start:i+1])
                        start = -1
            # 괄호 밖 텍스트도 있을 수 있지만, 무시
            if not memo_parts:
                memo_parts = [notes]
        else:
            memo_parts = [notes]

        for part in memo_parts:
            parsed = parse_memo(part, row['job_code'], row['location'] or '')
            if parsed and (parsed['phone'] or parsed['email']):
                parsed['_job_code'] = row['job_code']
                results.append(parsed)

    return results


def insert_employers(db_path: Path, records: list[dict]):
    """client_inquiries 테이블에 삽입"""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 5000")

    # 기존 memo_extract 소스 삭제 (재실행 가능)
    conn.execute("DELETE FROM client_inquiries WHERE source_file = ?", (SOURCE,))

    cols = [
        'submitted_at', 'email', 'school_name', 'location', 'contact_name',
        'phone', 'start_date', 'vacancies', 'teaching_age', 'schedule',
        'working_hours', 'salary_raw', 'housing_type', 'housing_detail',
        'travel_support', 'benefits', 'vacation', 'sick_leave', 'meal',
        'memo', 'source_file', 'loaded_at',
    ]
    ph = ', '.join('?' * len(cols))
    cs = ', '.join(cols)
    sql = f'INSERT INTO client_inquiries ({cs}) VALUES ({ph})'

    rows = []
    for r in records:
        rows.append([r.get(c) for c in cols])

    conn.executemany(sql, rows)
    conn.commit()

    total = conn.execute('SELECT COUNT(*) FROM client_inquiries').fetchone()[0]
    memo_count = conn.execute(
        'SELECT COUNT(*) FROM client_inquiries WHERE source_file = ?', (SOURCE,)
    ).fetchone()[0]
    conn.close()

    return total, memo_count


def main():
    ap = argparse.ArgumentParser(description='Extract employer info from job memos')
    ap.add_argument('--dry-run', action='store_true', help='Parse only, no DB write')
    args = ap.parse_args()

    print('=' * 65)
    print('  BRIDGE extract_employers.py')
    print('  내부 메모에서 고용주 연락처 추출')
    print('=' * 65)

    records = parse_all_memos(DB_PATH)
    print(f'\n  파싱 완료: {len(records)}건 추출')

    # 통계
    with_phone = sum(1 for r in records if r['phone'])
    with_email = sum(1 for r in records if r['email'])
    with_name  = sum(1 for r in records if r['contact_name'])
    with_school = sum(1 for r in records if r['school_name'] and not r['school_name'].startswith('('))
    print(f'  전화번호: {with_phone}건')
    print(f'  이메일:   {with_email}건')
    print(f'  담당자명: {with_name}건')
    print(f'  학원명:   {with_school}건')

    if args.dry_run:
        print('\n── DRY-RUN 미리보기 (처음 20건) ──')
        for r in records[:20]:
            print(f"  [{r.get('_job_code', '')}] {r['school_name'][:20]:20s} | "
                  f"{r['contact_name'][:10]:10s} | {r['phone'][:20]:20s} | {r['email'][:30]}")
        print(f'\n  총 {len(records)}건 — DB 쓰기 생략')
        return

    total, memo_count = insert_employers(DB_PATH, records)
    print(f'\n  DB 적재 완료')
    print(f'  메모 추출:       {memo_count}건')
    print(f'  client_inquiries 전체: {total}건')
    print('=' * 65)


if __name__ == '__main__':
    main()
