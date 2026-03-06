"""
BRIDGE 채용공고 비정형 텍스트 파서
- 비정형 메모/텍스트 → 정규화된 구조 데이터
- 원본 raw_text 100% 보존
- PII 자동 감지 및 분리
- Job ID 자동 생성 (BRJ-{REGION}-{YYMM}-{SEQ})

Usage:
    python parse_jobs.py --input raw_jobs.txt --db master.db
    python parse_jobs.py --input raw_jobs.txt --output parsed_jobs.json --dry-run
"""

from __future__ import annotations

import re
import json
import sqlite3
import hashlib
import argparse
import logging
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

# ─── 로깅 ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("bridge_parser")

# ─── 지역코드 매핑 ──────────────────────────────────────
REGION_MAP: dict[str, str] = {
    # 한글
    "서울": "SE", "부산": "BS", "대구": "DG", "인천": "IC",
    "광주": "GJ", "대전": "DJ", "울산": "US", "세종": "SJ",
    "경기": "GG", "강원": "GW", "충북": "CB", "충남": "CN",
    "전북": "JB", "전남": "JN", "경북": "KB", "경남": "KN",
    "제주": "JJ",
    # 영문
    "Seoul": "SE", "Busan": "BS", "Daegu": "DG", "Incheon": "IC",
    "Gwangju": "GJ", "Daejeon": "DJ", "Ulsan": "US", "Sejong": "SJ",
    "Gyeonggi": "GG", "Gangwon": "GW", "Chungbuk": "CB", "Chungnam": "CN",
    "Jeonbuk": "JB", "Jeonnam": "JN", "Gyeongbuk": "KB", "Gyeongnam": "KN",
    "Jeju": "JJ",
    # 축약/별칭
    "Gyeonggi-do": "GG", "경기도": "GG", "서울시": "SE", "서울특별시": "SE",
    "부산시": "BS", "부산광역시": "BS", "대구시": "DG", "대구광역시": "DG",
    "인천시": "IC", "인천광역시": "IC", "광주시": "GJ", "광주광역시": "GJ",
    "대전시": "DJ", "대전광역시": "DJ", "울산시": "US", "울산광역시": "US",
    "세종시": "SJ", "세종특별자치시": "SJ",
    "강원도": "GW", "충청북도": "CB", "충청남도": "CN",
    "전라북도": "JB", "전라남도": "JN", "경상북도": "KB", "경상남도": "KN",
    "제주도": "JJ", "제주특별자치도": "JJ",
}

# 역매핑: 코드 → 한글
REGION_NAME_MAP: dict[str, str] = {
    "SE": "서울", "BS": "부산", "DG": "대구", "IC": "인천",
    "GJ": "광주", "DJ": "대전", "US": "울산", "SJ": "세종",
    "GG": "경기", "GW": "강원", "CB": "충북", "CN": "충남",
    "JB": "전북", "JN": "전남", "KB": "경북", "KN": "경남",
    "JJ": "제주",
}

# ─── PII 패턴 ────────────────────────────────────────────
PII_PATTERNS = {
    "phone": re.compile(
        r"(?:010|011|016|017|018|019)"
        r"[-.\s]?\d{3,4}[-.\s]?\d{4}"
    ),
    "email": re.compile(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    ),
    "korean_name": re.compile(
        r"(?:원장|부장|대표|사장|팀장|실장|과장|부원장)"
        r"\s*[가-힣]{2,4}"
    ),
}

# ─── 필드 추출 패턴 ──────────────────────────────────────
FIELD_PATTERNS: dict[str, re.Pattern] = {
    "legacy_id": re.compile(r"Job\.?\s*(\d{3,5})", re.IGNORECASE),
    "start_date": re.compile(
        r"Starting?\s*Date\s*:\s*(.+?)(?:\n|$)", re.IGNORECASE
    ),
    "teaching_age": re.compile(
        r"Teaching\s*Age\s*:\s*(.+?)(?:\n|$)", re.IGNORECASE
    ),
    "class_size": re.compile(
        r"Class\s*size\s*:\s*(?:around\s*)?~?(\d+)", re.IGNORECASE
    ),
    "working_hours": re.compile(
        r"Working\s*Hours?\s*:\s*(.+?)(?:\n|$)", re.IGNORECASE
    ),
    "teaching_hours_weekly": re.compile(
        r"(?:Average\s*)?Teaching\s*Hours?\s*(?:per\s*Week)?\s*:\s*(\d+\.?\d*)",
        re.IGNORECASE,
    ),
    "salary_raw": re.compile(
        r"Monthly\s*Salary\s*:\s*(.+?)(?:\n|$)", re.IGNORECASE
    ),
    "vacation": re.compile(
        r"Vacation\s*:\s*(.+?)(?:\n|$)", re.IGNORECASE
    ),
    "native_count": re.compile(
        r"Native\s*Teacher.*?(?:Approx\.?\s*)?(\d+)", re.IGNORECASE
    ),
    "housing": re.compile(
        r"Housing\s*:\s*(.+?)(?:\n|$)", re.IGNORECASE
    ),
    "benefits": re.compile(
        r"Employee\s*Benefits?\s*:\s*(.+?)(?:\n\n|\Z)", re.IGNORECASE | re.DOTALL
    ),
    "degree": re.compile(
        r"(Bachelor'?s?\s*.+?)(?:\n|$)", re.IGNORECASE
    ),
}

# ─── 급여 파싱 ───────────────────────────────────────────
def parse_salary(raw: str) -> tuple[int, bool]:
    """급여 문자열 → (원 단위 금액, 협상가능여부)
    
    지원 포맷:
    - "2,40m KRW" / "2.40m" / "2,4m" → 2,400,000
    - "2,30 KRW" → 2,300,000 (m 없는 콤마 표기)
    - "230만원" → 2,300,000
    - "2300000" → 2,300,000
    """
    negotiable = "not negotiable" not in raw.lower()
    if "not negotiable" in raw.lower():
        negotiable = False

    # 원본에서 작업 (공백 제거하지 않음)
    lower = raw.lower()

    # 패턴 1: "2,40m" / "2.40m" / "2,4m" — 콤마/점이 소수점, m=백만
    m_match = re.search(r"(\d+)[,.](\d+)\s*m(?:\s|$|[^a-z])", lower)
    if m_match:
        whole = m_match.group(1)
        decimal = m_match.group(2)
        val = float(f"{whole}.{decimal}")
        return int(val * 1_000_000), negotiable

    # 패턴 1b: "2m" — 정수 + m
    m_int_match = re.search(r"(\d+)\s*m(?:\s|$|[^a-z])", lower)
    if m_int_match:
        return int(m_int_match.group(1)) * 1_000_000, negotiable

    # 패턴 2: "2,30 KRW" / "2.30 KRW" — m 없지만 KRW 단위, 콤마=소수점
    krw_match = re.search(r"(\d+)[,.](\d+)\s*krw", lower)
    if krw_match:
        whole = krw_match.group(1)
        decimal = krw_match.group(2)
        val = float(f"{whole}.{decimal}")
        return int(val * 1_000_000), negotiable

    # 패턴 3: "230만원" / "240만"
    man_match = re.search(r"(\d+)\s*만", raw)
    if man_match:
        return int(man_match.group(1)) * 10_000, negotiable

    # 패턴 4: 순수 숫자 6자리 이상
    cleaned = raw.replace(",", "").replace(" ", "")
    num_match = re.search(r"(\d{6,})", cleaned)
    if num_match:
        return int(num_match.group(1)), negotiable

    return 0, negotiable


# ─── 휴가일수 파싱 ───────────────────────────────────────
def parse_vacation(raw: str) -> int:
    """휴가 문자열 → 일수
    
    지원 포맷:
    - "16 days"
    - "total 5 weeks, plus 2 days for sick leave" → 27일
    - "5 weeks" → 25일
    """
    total = 0

    # weeks 먼저 체크 (days보다 앞에 올 수 있음)
    weeks_match = re.search(r"(?:total\s+)?(\d+)\s*weeks?", raw, re.IGNORECASE)
    if weeks_match:
        total += int(weeks_match.group(1)) * 5  # 근무일 기준

    # 추가 일수: "plus N days"
    plus_match = re.search(r"plus\s+(\d+)\s*days?", raw, re.IGNORECASE)
    if plus_match:
        total += int(plus_match.group(1))
        return total

    # weeks가 있었으면 반환
    if total > 0:
        return total

    # 단독 days
    days_match = re.search(r"(\d+)\s*days?", raw, re.IGNORECASE)
    if days_match:
        return int(days_match.group(1))

    return 0


# ─── 주거 파싱 ───────────────────────────────────────────
def parse_housing(raw: str) -> tuple[str, str]:
    """주거 문자열 → (타입, 상세)
    
    "provided or allowance" → both
    "allowance 400k" → allowance
    "provided" → provided
    """
    lower = raw.lower()
    has_provided = "provided" in lower
    has_allowance = "allowance" in lower

    if has_provided and has_allowance:
        return "both", raw.strip()
    elif has_allowance:
        return "allowance", raw.strip()
    elif has_provided:
        return "provided", raw.strip()
    elif "none" in lower or "no " in lower:
        return "none", raw.strip()
    return "other", raw.strip()


# ─── 복리후생 파싱 ───────────────────────────────────────
BENEFIT_KEYWORDS = [
    "visa sponsorship", "visa", "severance", "severance pay",
    "pension", "insurance", "paid vacation", "flexible lunch",
    "airfare", "airfare support", "renewal bonus", "bonus",
    "housing", "meal", "lunch",
]


def parse_benefits(raw: str) -> list[str]:
    """복리후생 문자열 → 키워드 리스트"""
    found = []
    lower = raw.lower()
    for kw in BENEFIT_KEYWORDS:
        if kw in lower:
            found.append(kw)
    return list(set(found))


# ─── 지역 감지 ───────────────────────────────────────────
def detect_region(text: str) -> tuple[str, str]:
    """텍스트에서 지역코드 + 한글명 추출"""
    # 영문 도시명 단독 라인 체크 (예: "Busan", "Seoul Guro")
    for line in text.split("\n")[:5]:
        stripped = line.strip()
        for name, code in REGION_MAP.items():
            if stripped.lower().startswith(name.lower()):
                return code, REGION_NAME_MAP.get(code, name)

    # 한글 지역명 스캔
    for name, code in REGION_MAP.items():
        if name in text:
            return code, REGION_NAME_MAP.get(code, name)

    return "XX", "미분류"


# ─── 구/군 추출 ──────────────────────────────────────────
def detect_district(text: str) -> str:
    """서울 구로, 부산 해운대 등 구/군 추출"""
    known_districts = {
        # 서울
        "Gangnam", "Gangbuk", "Gangdong", "Gangseo", "Guro", "Geumcheon",
        "Gwanak", "Gwangjin", "Jongno", "Jung", "Jungnang", "Dobong",
        "Dongdaemun", "Dongjak", "Mapo", "Seodaemun", "Seocho", "Seongdong",
        "Seongbuk", "Songpa", "Yangcheon", "Yeongdeungpo", "Yongsan", "Eunpyeong", "Nowon",
        # 부산
        "Haeundae", "Suyeong", "Busanjin", "Dongnae", "Nam", "Saha",
        "Sasang", "Yeonje", "Geumjeong", "Buk", "Gangseo",
        # 경기
        "Suwon", "Yongin", "Seongnam", "Goyang", "Bucheon", "Anyang",
        "Ansan", "Hwaseong", "Namyangju", "Uijeongbu", "Siheung", "Gimpo",
        "Gwangju", "Gwangmyeong", "Hanam", "Paju", "Pyeongtaek",
    }

    # 영문: "Seoul Guro", "Busan Haeundae"
    for line in text.split("\n")[:10]:
        stripped = line.strip()
        district_match = re.search(
            r"(?:Seoul|Busan|Daegu|Incheon|Gwangju|Daejeon|Ulsan|Suwon|Yongin)\s+([A-Z][a-z]+)",
            stripped,
        )
        if district_match:
            candidate = district_match.group(1)
            if candidate in known_districts:
                return candidate

    # 한글: "해운대구", "구로구", "수원시"
    gu_match = re.search(r"([가-힣]{2,4}(?:구|군))", text)
    if gu_match:
        return gu_match.group(1)

    # 한글 시 단위 (경기도 도시)
    si_match = re.search(r"([가-힣]{2,4}시)", text[:200])
    if si_match:
        return si_match.group(1)

    return ""


# ─── PII 추출 및 마스킹 ─────────────────────────────────
@dataclass
class ExtractedPII:
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)


def extract_pii(text: str) -> ExtractedPII:
    """텍스트에서 PII 추출 (암호화는 DB 저장 시 별도 처리)"""
    pii = ExtractedPII()
    pii.phones = PII_PATTERNS["phone"].findall(text)
    pii.emails = PII_PATTERNS["email"].findall(text)
    pii.names = PII_PATTERNS["korean_name"].findall(text)
    return pii


def mask_pii_in_text(text: str) -> str:
    """공개용 텍스트에서 PII 마스킹"""
    masked = text
    for phone in PII_PATTERNS["phone"].finditer(masked):
        masked = masked.replace(phone.group(), "***-****-****")
    for email in PII_PATTERNS["email"].finditer(masked):
        masked = masked.replace(email.group(), "****@****.***")
    for name in PII_PATTERNS["korean_name"].finditer(masked):
        masked = masked.replace(name.group(), "담당자 ****")
    return masked


# ─── F비자/교포 감지 ────────────────────────────────────
def detect_visa_flags(text: str) -> tuple[bool, bool, bool]:
    """(visa_sponsorship, f_visa_welcome, kyopo_welcome)"""
    lower = text.lower()
    f_visa = bool(re.search(r"f\s*visa", lower))
    kyopo = "kyopo" in lower or "교포" in text
    visa_sponsor = "visa sponsorship" in lower or "visa sponsor" in lower
    korea_only = "residing in korea" in lower or "한국 거주" in text
    return visa_sponsor, f_visa, kyopo


# ─── 메인 파서 ───────────────────────────────────────────
@dataclass
class ParsedJob:
    # 식별
    id: str = ""
    legacy_id: str = ""

    # 위치
    region: str = ""
    region_name: str = ""
    city: str = ""
    district: str = ""

    # PII (암호화 대상 — 여기서는 평문, DB 저장 시 암호화)
    pii_phones: list[str] = field(default_factory=list)
    pii_emails: list[str] = field(default_factory=list)
    pii_names: list[str] = field(default_factory=list)
    employer_display_name: str = ""

    # 채용 조건
    teaching_age: str = ""
    class_size: int = 0
    working_hours: str = ""
    teaching_hours_weekly: float = 0.0
    start_date: str = ""

    # 급여/복리
    salary_krw: int = 0
    salary_negotiable: bool = False
    housing_type: str = ""
    housing_detail: str = ""
    vacation_days: int = 0
    benefits: list[str] = field(default_factory=list)

    # 비자/자격
    visa_sponsorship: bool = True
    f_visa_welcome: bool = False
    kyopo_welcome: bool = False
    degree_requirement: str = ""
    korea_resident_only: bool = False

    # 원문
    raw_text: str = ""
    raw_source: str = "manual"

    # 메타
    native_teachers_count: int = 0
    status: str = "new"
    parse_confidence: float = 0.0
    parse_warnings: list[str] = field(default_factory=list)


def parse_job_block(text: str) -> ParsedJob:
    """단일 채용공고 텍스트 블록 → ParsedJob"""
    job = ParsedJob(raw_text=text.strip())
    warnings: list[str] = []
    matched_fields = 0
    total_fields = 12  # 핵심 필드 수

    # 1) Legacy ID
    lid = FIELD_PATTERNS["legacy_id"].search(text)
    if lid:
        job.legacy_id = lid.group(1)
        matched_fields += 1
    else:
        warnings.append("legacy_id 미감지")

    # 2) 지역
    job.region, job.region_name = detect_region(text)
    if job.region != "XX":
        matched_fields += 1
    else:
        warnings.append("region 미감지 — 수동 분류 필요")

    # 3) 구/군
    job.district = detect_district(text)

    # 4) PII 추출
    pii = extract_pii(text)
    job.pii_phones = pii.phones
    job.pii_emails = pii.emails
    job.pii_names = pii.names

    # 5) 공개용 표시명 생성
    if job.region_name and job.district:
        job.employer_display_name = f"{job.region_name} {job.district} 영어학원"
    elif job.region_name:
        job.employer_display_name = f"{job.region_name} 영어학원"

    # 6) Teaching Age
    ta = FIELD_PATTERNS["teaching_age"].search(text)
    if ta:
        job.teaching_age = ta.group(1).strip()
        matched_fields += 1

    # 7) Class Size
    cs = FIELD_PATTERNS["class_size"].search(text)
    if cs:
        job.class_size = int(cs.group(1))
        matched_fields += 1

    # 8) Working Hours
    wh = FIELD_PATTERNS["working_hours"].search(text)
    if wh:
        job.working_hours = wh.group(1).strip()
        matched_fields += 1

    # 9) Teaching Hours Weekly
    th = FIELD_PATTERNS["teaching_hours_weekly"].search(text)
    if th:
        job.teaching_hours_weekly = float(th.group(1))
        matched_fields += 1

    # 10) Start Date
    sd = FIELD_PATTERNS["start_date"].search(text)
    if sd:
        job.start_date = sd.group(1).strip()
        matched_fields += 1

    # 11) Salary
    sr = FIELD_PATTERNS["salary_raw"].search(text)
    if sr:
        job.salary_krw, job.salary_negotiable = parse_salary(sr.group(1))
        matched_fields += 1

    # 12) Vacation
    vc = FIELD_PATTERNS["vacation"].search(text)
    if vc:
        job.vacation_days = parse_vacation(vc.group(1))
        matched_fields += 1

    # 13) Native Teacher Count
    nc = FIELD_PATTERNS["native_count"].search(text)
    if nc:
        job.native_teachers_count = int(nc.group(1))
        matched_fields += 1

    # 14) Housing
    hs = FIELD_PATTERNS["housing"].search(text)
    if hs:
        job.housing_type, job.housing_detail = parse_housing(hs.group(1))
        matched_fields += 1

    # 15) Benefits
    bn = FIELD_PATTERNS["benefits"].search(text)
    if bn:
        job.benefits = parse_benefits(bn.group(1))
        matched_fields += 1

    # 16) Degree
    dg = FIELD_PATTERNS["degree"].search(text)
    if dg:
        job.degree_requirement = dg.group(1).strip()

    # 17) Visa flags
    job.visa_sponsorship, job.f_visa_welcome, job.kyopo_welcome = detect_visa_flags(text)
    job.korea_resident_only = bool(
        re.search(r"residing in korea|한국\s*거주", text, re.IGNORECASE)
    )

    # 신뢰도 계산
    job.parse_confidence = round(matched_fields / total_fields, 2)
    job.parse_warnings = warnings

    return job


# ─── 텍스트 분할 (다중 공고 분리) ─────────────────────────
def split_job_blocks(raw: str) -> list[str]:
    """
    여러 채용공고가 하나의 텍스트에 포함된 경우 분리.
    분리 기준:
    1. 빈 줄 2개 이상 + "Job." 패턴
    2. 괄호로 시작하는 한글 메모 라인 (새 블록 시작)
    """
    # 1차: "Job." 기준 분리
    blocks = re.split(r"\n\s*\n(?=\(?[가-힣].*\n|[A-Z][a-z]+\n)", raw)

    # 블록이 1개뿐이면 Job. 패턴으로 재시도
    if len(blocks) <= 1:
        blocks = re.split(r"\n\s*\n(?=\(?[가-힣])", raw)

    # 여전히 1개면 원본 그대로
    if len(blocks) <= 1:
        blocks = [raw]

    return [b.strip() for b in blocks if b.strip()]


# ─── Job ID 생성기 ───────────────────────────────────────
class JobIDGenerator:
    """BRJ-{REGION}-{YYMM}-{SEQ} ID 생성"""

    def __init__(self, db_path: Optional[str] = None):
        self._counters: dict[str, int] = {}
        self._db_path = db_path
        if db_path and Path(db_path).exists():
            self._load_from_db()

    def _load_from_db(self) -> None:
        """DB에서 기존 최대 순번 로드"""
        conn = sqlite3.connect(self._db_path)
        try:
            rows = conn.execute(
                "SELECT id FROM jobs WHERE id LIKE 'BRJ-%'"
            ).fetchall()
            for (job_id,) in rows:
                parts = job_id.split("-")
                if len(parts) == 4:
                    key = f"{parts[1]}-{parts[2]}"
                    seq = int(parts[3])
                    self._counters[key] = max(
                        self._counters.get(key, 0), seq
                    )
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()

    def generate(self, region_code: str, date: Optional[datetime] = None) -> str:
        dt = date or datetime.now()
        yymm = dt.strftime("%y%m")
        key = f"{region_code}-{yymm}"
        self._counters[key] = self._counters.get(key, 0) + 1
        seq = self._counters[key]
        return f"BRJ-{region_code}-{yymm}-{seq:03d}"


# ─── DB 저장 ─────────────────────────────────────────────
CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    legacy_id TEXT,
    region TEXT NOT NULL,
    region_name TEXT NOT NULL,
    city TEXT,
    district TEXT,
    enc_employer_name TEXT,
    enc_contact_name TEXT,
    enc_contact_phone TEXT,
    enc_contact_email TEXT,
    enc_contact_kakao TEXT,
    employer_display_name TEXT,
    teaching_age TEXT,
    class_size INTEGER,
    working_hours TEXT,
    teaching_hours_weekly REAL,
    start_date TEXT,
    salary_krw INTEGER,
    salary_negotiable BOOLEAN DEFAULT 0,
    housing_type TEXT,
    housing_detail TEXT,
    vacation_days INTEGER,
    benefits TEXT,
    visa_sponsorship BOOLEAN DEFAULT 1,
    f_visa_welcome BOOLEAN DEFAULT 0,
    kyopo_welcome BOOLEAN DEFAULT 0,
    degree_requirement TEXT,
    korea_resident_only BOOLEAN DEFAULT 0,
    raw_text TEXT NOT NULL,
    raw_source TEXT,
    native_teachers_count INTEGER,
    status TEXT DEFAULT 'new',
    parse_confidence REAL,
    parse_warnings TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    created_by TEXT DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS idx_jobs_region ON jobs(region);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_legacy ON jobs(legacy_id);

CREATE TABLE IF NOT EXISTS job_id_migration (
    legacy_id TEXT PRIMARY KEY,
    new_id TEXT NOT NULL,
    migrated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (new_id) REFERENCES jobs(id)
);
"""


def save_to_db(jobs: list[ParsedJob], db_path: str) -> int:
    """파싱된 채용공고 → SQLite DB 저장. PII는 placeholder (실제 암호화는 서버에서)"""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(CREATE_TABLES_SQL)

    saved = 0
    for job in jobs:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO jobs (
                    id, legacy_id, region, region_name, city, district,
                    enc_contact_phone, enc_contact_email, enc_contact_name,
                    employer_display_name,
                    teaching_age, class_size, working_hours,
                    teaching_hours_weekly, start_date,
                    salary_krw, salary_negotiable,
                    housing_type, housing_detail, vacation_days,
                    benefits, visa_sponsorship, f_visa_welcome,
                    kyopo_welcome, degree_requirement, korea_resident_only,
                    raw_text, raw_source, native_teachers_count,
                    status, parse_confidence, parse_warnings
                ) VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?,
                    ?, ?, ?,
                    ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?
                )""",
                (
                    job.id, job.legacy_id, job.region, job.region_name,
                    job.city, job.district,
                    # PII: 실제로는 AES-256-GCM 암호화 필요
                    # 여기서는 "PENDING_ENCRYPTION:" prefix로 표시
                    f"PENDING_ENC:{','.join(job.pii_phones)}" if job.pii_phones else None,
                    f"PENDING_ENC:{','.join(job.pii_emails)}" if job.pii_emails else None,
                    f"PENDING_ENC:{','.join(job.pii_names)}" if job.pii_names else None,
                    job.employer_display_name,
                    job.teaching_age, job.class_size, job.working_hours,
                    job.teaching_hours_weekly, job.start_date,
                    job.salary_krw, job.salary_negotiable,
                    job.housing_type, job.housing_detail, job.vacation_days,
                    json.dumps(job.benefits), job.visa_sponsorship,
                    job.f_visa_welcome, job.kyopo_welcome,
                    job.degree_requirement, job.korea_resident_only,
                    job.raw_text, job.raw_source, job.native_teachers_count,
                    job.status, job.parse_confidence,
                    json.dumps(job.parse_warnings),
                ),
            )

            # 마이그레이션 매핑
            if job.legacy_id:
                conn.execute(
                    "INSERT OR IGNORE INTO job_id_migration (legacy_id, new_id) VALUES (?, ?)",
                    (job.legacy_id, job.id),
                )

            saved += 1
        except Exception as e:
            log.error(f"DB 저장 실패 [{job.id}]: {e}")

    conn.commit()
    conn.close()
    return saved


# ─── 메인 실행 ───────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="BRIDGE 채용공고 비정형 텍스트 파서")
    parser.add_argument("--input", "-i", required=True, help="입력 파일 경로 (raw text)")
    parser.add_argument("--db", "-d", help="SQLite DB 경로 (저장 시)")
    parser.add_argument("--output", "-o", help="JSON 출력 경로 (dry-run 시)")
    parser.add_argument("--dry-run", action="store_true", help="DB 저장 없이 파싱만")
    parser.add_argument("--source", default="manual", help="데이터 소스 (manual/email/craigslist)")
    args = parser.parse_args()

    # 입력 읽기
    raw = Path(args.input).read_text(encoding="utf-8")
    log.info(f"입력 파일 로드: {args.input} ({len(raw):,} chars)")

    # 블록 분할
    blocks = split_job_blocks(raw)
    log.info(f"채용공고 블록 {len(blocks)}개 감지")

    # ID 생성기
    id_gen = JobIDGenerator(args.db)

    # 파싱
    parsed_jobs: list[ParsedJob] = []
    for i, block in enumerate(blocks):
        job = parse_job_block(block)
        job.raw_source = args.source
        job.id = id_gen.generate(job.region)

        log.info(
            f"  [{i+1}/{len(blocks)}] {job.id} "
            f"(legacy={job.legacy_id or 'N/A'}, "
            f"region={job.region_name}, "
            f"confidence={job.parse_confidence:.0%})"
        )
        if job.parse_warnings:
            for w in job.parse_warnings:
                log.warning(f"    ⚠ {w}")

        parsed_jobs.append(job)

    # 출력
    if args.dry_run or args.output:
        output_path = args.output or "parsed_jobs.json"
        # PII 제거한 안전한 출력
        safe_output = []
        for j in parsed_jobs:
            d = asdict(j)
            d["pii_phones"] = [f"****{p[-4:]}" for p in j.pii_phones]
            d["pii_emails"] = ["****@****" for _ in j.pii_emails]
            d["pii_names"] = ["****" for _ in j.pii_names]
            safe_output.append(d)

        Path(output_path).write_text(
            json.dumps(safe_output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log.info(f"JSON 출력: {output_path}")

    elif args.db:
        saved = save_to_db(parsed_jobs, args.db)
        log.info(f"DB 저장 완료: {saved}/{len(parsed_jobs)}건 → {args.db}")

    else:
        log.error("--db 또는 --output/--dry-run 중 하나 지정 필요")

    # 요약
    log.info("=" * 60)
    log.info(f"총 파싱: {len(parsed_jobs)}건")
    avg_conf = (
        sum(j.parse_confidence for j in parsed_jobs) / len(parsed_jobs)
        if parsed_jobs
        else 0
    )
    log.info(f"평균 파싱 신뢰도: {avg_conf:.0%}")
    low_conf = [j for j in parsed_jobs if j.parse_confidence < 0.5]
    if low_conf:
        log.warning(f"낮은 신뢰도 ({len(low_conf)}건) — 수동 검토 권장:")
        for j in low_conf:
            log.warning(f"  {j.id} (legacy={j.legacy_id}): {j.parse_confidence:.0%}")


if __name__ == "__main__":
    main()
