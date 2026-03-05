"""
parse_jobs.py — 비정형 채용공고 텍스트 → 구조화 데이터
Usage:
  python parse_jobs.py --input raw.txt --db master.db
  python parse_jobs.py --input raw.txt --output parsed.json --dry-run
"""
import argparse
import json
import re
import sqlite3
import sys
import os
from datetime import datetime, timezone

# ── Region codes ──
REGION_CODES = {
    "Seoul": "SE", "서울": "SE", "Busan": "BS", "부산": "BS",
    "Daegu": "DG", "대구": "DG", "Incheon": "IC", "인천": "IC",
    "Gwangju": "GJ", "광주": "GJ", "Daejeon": "DJ", "대전": "DJ",
    "Ulsan": "US", "울산": "US", "Sejong": "SJ", "세종": "SJ",
    "Gyeonggi": "GG", "경기": "GG", "Gangwon": "GW", "강원": "GW",
    "Chungbuk": "CB", "충북": "CB", "Chungnam": "CN", "충남": "CN",
    "Jeonbuk": "JB", "전북": "JB", "Jeonnam": "JN", "전남": "JN",
    "Gyeongbuk": "KB", "경북": "KB", "Gyeongnam": "KN", "경남": "KN",
    "Jeju": "JJ", "제주": "JJ",
    "Suwon": "GG", "Seongnam": "GG", "Yongin": "GG", "Goyang": "GG",
    "Bucheon": "GG", "Anyang": "GG", "Hwaseong": "GG", "Pyeongtaek": "GG",
    "Cheonan": "CN", "Cheongju": "CB", "Jeonju": "JB",
    "Pohang": "KB", "Changwon": "KN", "Gimhae": "KN",
}

REGION_NAMES = {
    "SE": "서울", "BS": "부산", "DG": "대구", "IC": "인천",
    "GJ": "광주", "DJ": "대전", "US": "울산", "SJ": "세종",
    "GG": "경기", "GW": "강원", "CB": "충북", "CN": "충남",
    "JB": "전북", "JN": "전남", "KB": "경북", "KN": "경남",
    "JJ": "제주", "XX": "기타",
}


def get_region_code(text: str) -> str:
    for key, code in REGION_CODES.items():
        if key.lower() in text.lower():
            return code
    return "XX"


# ── PII Detection ──
PII_PHONE = re.compile(r'(?:010|011|016|017|018|019)[-.\s]?\d{3,4}[-.\s]?\d{4}|(?:\+82|82)\s?10[-.\s]?\d{4}[-.\s]?\d{4}|\d{2,3}[-.\s]\d{3,4}[-.\s]\d{4}')
PII_EMAIL = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
PII_NAME_KR = re.compile(r'[가-힣]{2,4}(?:\s*(?:원장|선생|대표|사장|실장|팀장))')


def extract_pii(text: str) -> dict:
    pii = {}
    phones = PII_PHONE.findall(text)
    if phones:
        pii["contact_phone"] = phones[0]
    emails = PII_EMAIL.findall(text)
    if emails:
        pii["contact_email"] = emails[0]
    names = PII_NAME_KR.findall(text)
    if names:
        pii["contact_name"] = names[0]
    return pii


# ── Salary Parsing ──
def parse_salary(text: str) -> tuple[int | None, bool]:
    """Return (salary_krw, negotiable)."""
    if not text:
        return None, False
    negotiable = bool(re.search(r'negotiab', text, re.IGNORECASE))
    if re.search(r'not\s+negotiab|non[-\s]?negotiab', text, re.IGNORECASE):
        negotiable = False
    # "2,40m" → "2.40m" (comma as decimal separator)
    text_norm = re.sub(r'(\d),(\d{1,2})(?=\s*m)', r'\1.\2', text)
    text_clean = text_norm.replace(",", "").replace(" ", "")
    # "2.40m" or "2.4m" patterns (millions KRW)
    m = re.search(r'(\d+\.?\d*)m', text_clean, re.IGNORECASE)
    if m:
        val = float(m.group(1))
        if val < 100:
            return int(val * 1_000_000), negotiable
        return int(val), negotiable
    # Plain number patterns
    nums = re.findall(r'(\d+\.?\d*)', text_clean)
    if nums:
        val = float(nums[0])
        if val < 10:
            return int(val * 1_000_000), negotiable
        if val < 1000:
            return int(val * 10_000), negotiable
        return int(val), negotiable
    return None, negotiable


# ── Vacation Parsing ──
def parse_vacation(text: str) -> int | None:
    """Parse vacation to total days."""
    if not text:
        return None
    total = 0
    # "X weeks"
    wm = re.findall(r'(\d+)\s*weeks?', text, re.IGNORECASE)
    for w in wm:
        total += int(w) * 5
    # "X days"
    dm = re.findall(r'(\d+)\s*days?', text, re.IGNORECASE)
    for d in dm:
        total += int(d)
    return total if total > 0 else None


# ── Housing Parsing ──
def parse_housing(text: str) -> tuple[str, str]:
    """Return (housing_type, housing_detail)."""
    if not text:
        return "", ""
    t = text.lower()
    if "provided" in t and "allowance" in t:
        return "both", text
    if "provided" in t or "studio" in t or "apartment" in t:
        return "provided", text
    if "allowance" in t:
        return "allowance", text
    if "none" in t or "no " in t:
        return "none", text
    return "other", text


# ── Main Parser ──
def parse_raw_text(raw: str) -> dict:
    """Parse a raw job text block into structured fields."""
    result: dict = {
        "raw_text": raw,
        "parse_warnings": [],
    }
    confidence = 0.0
    fields_found = 0
    total_fields = 8

    lines = raw.strip().split("\n")

    # Location
    for line in lines[:5]:
        rc = get_region_code(line)
        if rc != "XX":
            result["region"] = rc
            result["region_name"] = REGION_NAMES.get(rc, "기타")
            # city extraction
            for key in REGION_CODES:
                if key.lower() in line.lower():
                    result["city"] = key
                    break
            fields_found += 1
            break

    # Salary
    salary_line = ""
    for line in lines:
        if re.search(r'salary|pay|krw|만원|월급', line, re.IGNORECASE):
            salary_line = line
            break
    if not salary_line:
        for line in lines:
            if re.search(r'\d+[.,]?\d*m?\s*(?:krw|won)?', line, re.IGNORECASE):
                salary_line = line
                break
    if salary_line:
        krw, neg = parse_salary(salary_line)
        if krw:
            result["salary_krw"] = krw
            result["salary_negotiable"] = 1 if neg else 0
            fields_found += 1

    # Vacation
    for line in lines:
        if re.search(r'vacation|holiday|leave|휴가', line, re.IGNORECASE):
            days = parse_vacation(line)
            if days:
                result["vacation_days"] = days
                fields_found += 1
            break

    # Housing
    for line in lines:
        if re.search(r'housing|accommodation|숙소|주거', line, re.IGNORECASE):
            ht, hd = parse_housing(line)
            result["housing_type"] = ht
            result["housing_detail"] = hd
            fields_found += 1
            break

    # Teaching age
    for line in lines:
        if re.search(r'kindy|kinder|elementary|elem|middle|high|adult|유치|초등|중등|고등', line, re.IGNORECASE):
            result["teaching_age"] = line.strip()
            fields_found += 1
            break

    # Working hours
    for line in lines:
        m = re.search(r'(\d{1,2}:\d{2})\s*[~\-]\s*(\d{1,2}:\d{2})', line)
        if m:
            result["working_hours"] = f"{m.group(1)}~{m.group(2)}"
            fields_found += 1
            break

    # Start date
    for line in lines:
        if re.search(r'start|시작|입사', line, re.IGNORECASE):
            result["start_date"] = line.strip()
            fields_found += 1
            break

    # Benefits
    for line in lines:
        if re.search(r'benefit|visa|severance|pension|insurance|복리', line, re.IGNORECASE):
            result["benefits"] = line.strip()
            fields_found += 1
            break

    # PII
    pii = extract_pii(raw)
    if pii:
        result["_pii"] = pii
        result["parse_warnings"].append(f"PII detected: {', '.join(pii.keys())}")

    # Confidence
    confidence = round(fields_found / total_fields, 2)
    result["parse_confidence"] = confidence
    result["parse_warnings"] = json.dumps(result["parse_warnings"], ensure_ascii=False)

    return result


def generate_brj_id(conn: sqlite3.Connection, region_code: str) -> str:
    now = datetime.now(timezone.utc)
    yymm = now.strftime("%y%m")
    prefix = f"BRJ-{region_code}-{yymm}-"
    row = conn.execute(
        "SELECT brj_id FROM jobs WHERE brj_id LIKE ? ORDER BY brj_id DESC LIMIT 1",
        (f"{prefix}%",)
    ).fetchone()
    if row:
        last_seq = int(row[0].split("-")[-1])
        return f"{prefix}{last_seq + 1:03d}"
    return f"{prefix}001"


def main():
    parser = argparse.ArgumentParser(description="Parse raw job text → structured data")
    parser.add_argument("--input", required=True, help="Raw text file")
    parser.add_argument("--db", default=None, help="SQLite DB path (insert mode)")
    parser.add_argument("--output", default=None, help="JSON output path")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, no DB write")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found")
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        raw = f.read()

    # Split by double newline for multiple jobs
    blocks = re.split(r'\n{3,}', raw.strip())
    if not blocks:
        blocks = [raw]

    results = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        parsed = parse_raw_text(block)
        results.append(parsed)

    print(f"Parsed {len(results)} job(s)")
    for i, r in enumerate(results):
        print(f"  [{i+1}] region={r.get('region','?')}, salary={r.get('salary_krw','?')}, "
              f"vacation={r.get('vacation_days','?')}d, confidence={r.get('parse_confidence',0)}")

    if args.output or args.dry_run:
        out = json.dumps(results, indent=2, ensure_ascii=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"Output: {args.output}")
        else:
            print(out)
        return

    if args.db:
        conn = sqlite3.connect(args.db)
        conn.execute("PRAGMA busy_timeout = 5000")
        now = datetime.now(timezone.utc).isoformat()
        inserted = 0
        for parsed in results:
            region = parsed.get("region", "XX")
            brj_id = generate_brj_id(conn, region)
            conn.execute("""
                INSERT INTO jobs (
                    brj_id, region, region_name, city,
                    salary_krw, salary_negotiable, vacation_days,
                    housing_type, housing_detail, teaching_age,
                    working_hours, start_date, benefits,
                    raw_text, raw_source, parse_confidence, parse_warnings,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)
            """, (
                brj_id, region, parsed.get("region_name", "기타"), parsed.get("city", ""),
                parsed.get("salary_krw"), parsed.get("salary_negotiable", 0),
                parsed.get("vacation_days"), parsed.get("housing_type", ""),
                parsed.get("housing_detail", ""), parsed.get("teaching_age", ""),
                parsed.get("working_hours", ""), parsed.get("start_date", ""),
                parsed.get("benefits", ""), parsed.get("raw_text", ""),
                "manual_parse", parsed.get("parse_confidence", 0),
                parsed.get("parse_warnings", "[]"), now,
            ))
            inserted += 1
        conn.commit()
        conn.close()
        print(f"Inserted {inserted} jobs into DB")


if __name__ == "__main__":
    main()
