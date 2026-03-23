"""
BRIDGE Document Processor v2.0
후보자 이력서/커버레터에서 PII 삭제 + 강사번호 입력

사용법:
  python doc_processor.py process <파일/폴더> [--number N] [--output DIR] [--dry]
  python doc_processor.py lookup <이름 또는 이메일>

예시:
  python doc_processor.py process resume.docx --number 3057
  python doc_processor.py process resume.pdf --number 3057
  python doc_processor.py process "Q:/incoming/" --dry         # 미리보기만
  python doc_processor.py lookup "Tahliso"

지원 형식: .docx (서식 보존), .pdf (인-플레이스 redaction)
Python: "D:/Phtyon 3/python.exe"
의존성: python-docx, PyMuPDF (fitz), python-dotenv, cryptography
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# ── 경로 ──────────────────────────────────────────────
BASE_DIR = Path("Q:/Claudework/bridge base")
DB_PATH = BASE_DIR / "master.db"
ENV_PATH = BASE_DIR / ".env"
DEFAULT_OUTPUT = BASE_DIR / "tools" / "processed_docs" / "processed"
INCOMING_DIR = BASE_DIR / "tools" / "processed_docs" / "incoming"
BACKUP_DIR = BASE_DIR / "tools" / "processed_docs" / "originals"
LOG_DIR = BASE_DIR / "tools" / "processed_docs" / "logs"


# ══════════════════════════════════════════════════════
#  1. DB 접근 + 암호화 처리
# ══════════════════════════════════════════════════════

_db_conn = None  # 세션 내 연결 재사용


def _get_db():
    """DB 연결 (세션 내 재사용)"""
    global _db_conn
    if _db_conn is None:
        if not DB_PATH.exists():
            print(f"[ERROR] DB not found: {DB_PATH}")
            sys.exit(1)
        _db_conn = sqlite3.connect(str(DB_PATH))
        _db_conn.row_factory = sqlite3.Row
    return _db_conn


def _try_decrypt(value):
    """암호화 필드 복호화 시도. 실패 시 원문 반환."""
    if not value or not value.strip():
        return value or ""
    try:
        # security_vault가 로드 가능할 때만 복호화 시도
        sys.path.insert(0, str(BASE_DIR))
        from dotenv import load_dotenv
        load_dotenv(str(ENV_PATH))
        from security_vault import decrypt_field
        return decrypt_field(value)
    except (ImportError, EnvironmentError):
        return value
    except (ValueError, Exception):
        # base64 디코딩 실패 등 → 평문으로 간주
        return value


def lookup_candidate(query: str):
    """이름/이메일로 후보자 검색"""
    db = _get_db()
    if "@" in query:
        rows = db.execute(
            "SELECT sheet_number, full_name, nationality, email "
            "FROM candidates WHERE email LIKE ? LIMIT 10",
            (f"%{query}%",),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT sheet_number, full_name, nationality, email "
            "FROM candidates WHERE full_name LIKE ? LIMIT 10",
            (f"%{query}%",),
        ).fetchall()
    return [(r[0], _try_decrypt(r[1]), _try_decrypt(r[2]), _try_decrypt(r[3])) for r in rows]


def get_candidate(number: int):
    """sheet_number로 후보자 조회 → dict or None"""
    db = _get_db()
    row = db.execute(
        "SELECT sheet_number, full_name, nationality, email, "
        "mobile_phone, kakaotalk, current_location "
        "FROM candidates WHERE sheet_number = ?",
        (number,),
    ).fetchone()
    if not row:
        return None
    return {
        "sheet_number": row[0],
        "full_name": _try_decrypt(row[1]),
        "nationality": _try_decrypt(row[2]),
        "email": _try_decrypt(row[3]),
        "mobile_phone": _try_decrypt(row[4]),
        "kakaotalk": _try_decrypt(row[5]),
        "current_location": _try_decrypt(row[6]),
    }


# ══════════════════════════════════════════════════════
#  2. PII 패턴 정의
# ══════════════════════════════════════════════════════

RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

# 전화번호: 7자리+ 숫자를 포함하는 시퀀스만 (날짜·연도 충돌 방지)
RE_PHONE = re.compile(
    r"(?:\+?\d{1,3}[\s\-.]?)?\(?\d{2,4}\)?[\s\-.]?\d{3,4}[\s\-.]?\d{3,4}\b"
)

RE_URL = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", re.I)

RE_LINKEDIN = re.compile(
    r"(?:linkedin\.com/in/[^\s<>\"']+|linkedin\s*:?\s*[^\s,;\n]+)", re.I
)

RE_KAKAO = re.compile(
    r"(?:kakao(?:talk)?|카카오(?:톡)?)\s*:?\s*[A-Za-z0-9._\-]+", re.I
)

RE_SNS = re.compile(
    r"(?:instagram|facebook|twitter|whatsapp|wechat|skype|telegram)"
    r"\s*:?\s*[@]?[A-Za-z0-9._\-]+",
    re.I,
)

RE_KR_ADDRESS = re.compile(
    r"(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)"
    r"(?:특별시|광역시|도|특별자치시|특별자치도)?"
    r"[\s]?(?:\S+(?:시|군|구|읍|면|동|리|로|길|번지)[\s]?){0,5}",
    re.UNICODE,
)

RE_PASSPORT = re.compile(r"\b[A-Z]{1,2}\d{7,8}\b")

# 한국 도시/지역 키워드 (소문자)
KR_KEYWORDS = frozenset([
    "korea", "seoul", "busan", "daegu", "incheon", "gwangju",
    "daejeon", "ulsan", "sejong", "gyeonggi", "gangwon",
    "chungbuk", "chungnam", "jeonbuk", "jeonnam",
    "gyeongbuk", "gyeongnam", "jeju",
    "south korea", "republic of korea", "rok",
    "한국", "서울", "부산", "대구", "인천", "광주", "대전", "울산",
    "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
    "suwon", "seongnam", "goyang", "yongin", "changwon",
    "ansan", "anyang", "namyangju", "hwaseong", "pyeongtaek",
    "gimpo", "gwacheon", "uijeongbu", "paju", "yangju",
    "pocheon", "dongducheon", "guri", "hanam", "icheon",
    "osan", "gunpo", "uiwang", "siheung", "bucheon",
    "jeonju", "cheongju", "cheonan", "asan",
    "gimhae", "yangsan", "geoje", "tongyeong",
    "mokpo", "yeosu", "suncheon", "gwangyang",
    "gyeongju", "pohang", "andong", "gumi",
    "chuncheon", "wonju", "gangneung", "sokcho",
    "itaewon", "gangnam", "hongdae", "sinchon", "mapo",
    "jamsil", "songpa", "yongsan", "nowon", "bundang",
    "ilsan", "dongtan", "pangyo",
])

# PII 라벨 → 해당 줄 전체 삭제
# 주의: "line", "cell" 등 짧은 단어는 ":" 필수 조건으로 오탐 방지
PII_LINE_LABELS = [
    # 연락처 (colon 필수)
    ("email", True), ("e-mail", True),
    ("phone", True), ("telephone", True), ("mobile", True),
    ("cell", True), ("tel", True),
    # SNS (colon 필수)
    ("kakao", True), ("kakaotalk", True),
    ("line id", True), ("line", True),
    ("skype", True), ("whatsapp", True),
    ("wechat", True), ("telegram", True),
    ("instagram", True), ("facebook", True), ("twitter", True),
    # 링크
    ("linkedin", True), ("website", True), ("personal website", True),
    ("portfolio", True),
    # 신원
    ("passport", True), ("passport number", True), ("passport no", True),
    # 한국어
    ("이메일", True), ("전화", True), ("연락처", True),
    ("카카오", True), ("여권", True),
]

# 위치 라벨 → 한국이면 "Korea"로 변환
LOCATION_LABELS = [
    "current location", "current address", "address", "location",
    "residence", "residing in", "living in", "based in",
    "city", "province", "country of residence",
    "현재 위치", "거주지", "주소", "현위치",
]

# 직장명 라벨 → 값 삭제 (institution/university 제외)
WORKPLACE_LABELS = [
    "current employer", "employer", "company", "workplace",
    "school name", "academy name", "hagwon",
    "현 직장", "근무지", "학원명", "학교명",
]


# ══════════════════════════════════════════════════════
#  3. PII 삭제 엔진
# ══════════════════════════════════════════════════════

def _is_korea(text: str) -> bool:
    lower = text.lower().strip()
    return any(kw in lower for kw in KR_KEYWORDS)


def _name_variants(full_name: str) -> list[str]:
    """
    이름의 모든 인식 가능 변형 생성.
    - 풀네임, First Last, Last First, 각 단어(3글자 이상만)
    - 세미콜론/괄호 별명 처리
    긴 변형부터 정렬 (greedy 매칭)
    """
    if not full_name or not full_name.strip():
        return []

    raw = full_name.strip()
    variants = set()
    variants.add(raw)

    # 별명 분리: "Jashen Arianne ; Shen" → main + nickname
    main_name = raw
    if ";" in raw:
        parts = raw.split(";", 1)
        main_name = parts[0].strip()
        nick = parts[1].strip()
        variants.add(main_name)
        if nick and len(nick) > 2:
            variants.add(nick)

    if "(" in main_name:
        clean = re.sub(r"\s*\([^)]*\)", "", main_name).strip()
        nick_m = re.search(r"\(([^)]+)\)", main_name)
        variants.add(clean)
        if nick_m and len(nick_m.group(1)) > 2:
            variants.add(nick_m.group(1))
        main_name = clean

    words = main_name.split()

    if len(words) >= 2:
        # First Last
        variants.add(f"{words[0]} {words[-1]}")
        # Last, First
        variants.add(f"{words[-1]}, {words[0]}")
        # Last First
        variants.add(f"{words[-1]} {words[0]}")
        # 모든 인접 2-word 조합 (중간이름 포함)
        for i in range(len(words) - 1):
            variants.add(f"{words[i]} {words[i+1]}")

    # 개별 단어 (3글자 이상만, 너무 짧으면 오탐)
    for w in words:
        if len(w) >= 3:
            variants.add(w)

    # 긴 것부터 매칭 (greedy)
    return sorted(variants, key=len, reverse=True)


def _should_skip_line(stripped_lower: str) -> bool:
    """PII 라벨로 시작하는 줄인지 판별"""
    for label, needs_colon in PII_LINE_LABELS:
        if not stripped_lower.startswith(label):
            continue
        rest = stripped_lower[len(label):]
        if not rest:
            return True  # 라벨만 있는 줄
        first_char = rest.lstrip()[0] if rest.lstrip() else ""
        if needs_colon and first_char == ":":
            return True
        if not needs_colon:
            if first_char in (":", " "):
                return True
    return False


def remove_pii(text: str, candidate: dict = None) -> tuple[str, list[str]]:
    """
    텍스트에서 PII 삭제.
    Returns: (cleaned_text, list[삭제 로그])
    """
    log = []

    # ── Pass 1: 줄 단위 PII 라벨 삭제 ──
    lines = text.split("\n")
    kept_lines = []
    for line in lines:
        stripped = line.strip().lower()
        if stripped and _should_skip_line(stripped):
            log.append(f"LINE_DEL: {line.strip()[:80]}")
            continue
        kept_lines.append(line)
    result = "\n".join(kept_lines)

    # ── Pass 2: regex 기반 인라인 삭제 ──
    def _sub(pattern, repl, tag):
        nonlocal result
        def replacer(m):
            log.append(f"{tag}: {m.group()[:60]}")
            return repl
        result = pattern.sub(replacer, result)

    # 여권 먼저 (전화번호 regex와 숫자 충돌 방지)
    _sub(RE_PASSPORT, "", "PASSPORT")
    _sub(RE_EMAIL, "", "EMAIL")
    _sub(RE_LINKEDIN, "", "LINKEDIN")
    _sub(RE_KAKAO, "", "KAKAO")
    _sub(RE_SNS, "", "SNS")
    _sub(RE_URL, "", "URL")

    # 전화번호 (7자리+ 숫자만)
    def phone_replacer(m):
        digits = re.sub(r"\D", "", m.group())
        if len(digits) >= 7:
            log.append(f"PHONE: {m.group()[:40]}")
            return ""
        return m.group()
    result = RE_PHONE.sub(phone_replacer, result)

    # 한국 주소 → "Korea"
    def addr_replacer(m):
        log.append(f"KR_ADDR→Korea: {m.group()[:40]}")
        return "Korea"
    result = RE_KR_ADDRESS.sub(addr_replacer, result)

    # ── Pass 3: 후보자별 PII (DB에서 가져온 값) ──
    if candidate:
        name = candidate.get("full_name", "")
        if name:
            for variant in _name_variants(name):
                pat = re.compile(re.escape(variant), re.IGNORECASE)
                if pat.search(result):
                    log.append(f"NAME: {variant}")
                    result = pat.sub("", result)

        # DB에서 가져온 이메일/전화/카카오도 직접 삭제
        for field in ("email", "mobile_phone", "kakaotalk"):
            val = candidate.get(field, "")
            if val and len(val) > 2:
                escaped = re.escape(val)
                if re.search(escaped, result, re.I):
                    log.append(f"DB_{field.upper()}: {val[:30]}")
                    result = re.sub(escaped, "", result, flags=re.I)

    # ── Pass 4: 위치/직장 라벨 값 처리 ──
    for label in LOCATION_LABELS:
        pat = re.compile(rf"({re.escape(label)}\s*:?\s*)(.+)", re.I)
        def _loc_rep(m):
            prefix, value = m.group(1), m.group(2).strip()
            if _is_korea(value):
                log.append(f"LOC→Korea: {value[:40]}")
                return f"{prefix}Korea"
            return m.group(0)
        result = pat.sub(_loc_rep, result)

    for label in WORKPLACE_LABELS:
        pat = re.compile(rf"({re.escape(label)}\s*:?\s*)(.+)", re.I)
        def _work_rep(m):
            log.append(f"WORKPLACE_DEL: {m.group(2).strip()[:40]}")
            return m.group(1)
        result = pat.sub(_work_rep, result)

    # 빈줄 정리
    result = re.sub(r"\n{3,}", "\n\n", result)
    # 빈 라벨줄 정리 (라벨: 만 남은 줄)
    result = re.sub(r"^[ \t]*\w[\w\s]*:\s*$", "", result, flags=re.MULTILINE)
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result, log


# ══════════════════════════════════════════════════════
#  4. DOCX 처리 (서식 보존)
# ══════════════════════════════════════════════════════

def _replace_in_runs(paragraph, cleaned_text):
    """
    단락의 run들에서 텍스트를 교체하되 서식을 최대한 보존.
    전략: 각 run의 텍스트 내에서 PII 부분만 교체.
    """
    runs = paragraph.runs
    if not runs:
        return

    original_full = "".join(r.text for r in runs)
    if not original_full.strip():
        return

    # 삭제된 텍스트가 없으면 스킵
    if original_full == cleaned_text:
        return

    # run이 1개면 단순 교체 (서식 유지)
    if len(runs) == 1:
        runs[0].text = cleaned_text
        return

    # run이 여러개: cleaned_text를 run 경계에 맞춰 분배
    # 전략: 각 run의 원래 길이 비율로 배분
    # 단, PII가 run 경계를 걸칠 수 있으므로 최선의 근사치 사용
    # cleaned가 비면 모든 run을 비움
    if not cleaned_text.strip():
        for r in runs:
            r.text = ""
        return

    # 원문과 cleaned의 공통 접두사/접미사 기반 매칭
    # 실용적 접근: 첫 run에 전체 cleaned, 나머지 비움
    # (완벽한 run-level 매칭은 diff 알고리즘이 필요하여 실무 대비 과도)
    #
    # 개선: 각 run의 텍스트가 cleaned에 그대로 존재하면 유지,
    #       아니면 cleaned에서 해당 위치 텍스트 추출
    pos = 0
    remaining = cleaned_text
    for i, run in enumerate(runs):
        orig_len = len(run.text)
        if i == len(runs) - 1:
            # 마지막 run에 나머지 전부
            run.text = remaining
        else:
            # 원래 run의 텍스트가 remaining 시작부에 있으면 유지
            if remaining.startswith(run.text):
                remaining = remaining[orig_len:]
            else:
                # PII가 이 run에 있었음 → 이 run 비우고 다음으로
                run.text = ""


def process_docx(filepath: Path, brj_number: int, candidate: dict = None, dry: bool = False):
    """DOCX 처리: PII 삭제 + 번호 삽입. Returns (doc, log_entries)"""
    import docx

    doc = docx.Document(str(filepath))
    all_logs = []

    def _process_paragraphs(paragraphs, section_name="body"):
        for para in paragraphs:
            original = para.text
            if not original.strip():
                continue
            cleaned, log = remove_pii(original, candidate)
            if cleaned != original:
                all_logs.extend([f"[{section_name}] {l}" for l in log])
                if not dry:
                    _replace_in_runs(para, cleaned)

    # 본문
    _process_paragraphs(doc.paragraphs, "body")

    # 테이블
    for ti, table in enumerate(doc.tables):
        for row in table.rows:
            for cell in row.cells:
                _process_paragraphs(cell.paragraphs, f"table{ti}")

    # 헤더/푸터
    for si, section in enumerate(doc.sections):
        for hf_name, hf in [("header", section.header), ("footer", section.footer)]:
            if hf and hf.paragraphs:
                _process_paragraphs(hf.paragraphs, f"{hf_name}{si}")
        # first_page 헤더/푸터
        try:
            fph = section.first_page_header
            if fph and fph.paragraphs:
                _process_paragraphs(fph.paragraphs, f"first_header{si}")
        except Exception:
            pass
        try:
            fpf = section.first_page_footer
            if fpf and fpf.paragraphs:
                _process_paragraphs(fpf.paragraphs, f"first_footer{si}")
        except Exception:
            pass

    # 번호 삽입 (최상단)
    if not dry:
        first_para = doc.paragraphs[0] if doc.paragraphs else None
        if first_para:
            new_para = first_para.insert_paragraph_before(str(brj_number))
            run = new_para.runs[0]
            run.bold = True
            run.font.size = docx.shared.Pt(18)
        else:
            p = doc.add_paragraph(str(brj_number))
            p.runs[0].bold = True
            p.runs[0].font.size = docx.shared.Pt(18)

    return doc, all_logs


# ══════════════════════════════════════════════════════
#  5. PDF 처리 (인-플레이스 redaction)
# ══════════════════════════════════════════════════════

def process_pdf(filepath: Path, brj_number: int, candidate: dict = None, dry: bool = False):
    """
    PDF 처리: PyMuPDF redaction으로 PII를 흰색 사각형으로 덮기.
    원본 서식/이미지/레이아웃 보존.
    Returns (output_path or None, log_entries)
    """
    import fitz

    doc = fitz.open(str(filepath))
    all_logs = []

    # 모든 PII 패턴을 수집
    pii_patterns = _build_search_patterns(candidate)

    for page_num, page in enumerate(doc):
        text = page.get_text()

        # 줄 단위 PII 라벨 검사 → redact 대상 텍스트 수집
        redact_texts = set()

        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue

            # PII 라벨 줄 → 전체 줄 redact
            if _should_skip_line(stripped.lower()):
                redact_texts.add(stripped)
                all_logs.append(f"[page{page_num}] LINE_DEL: {stripped[:60]}")
                continue

        # regex 패턴 매칭
        for pattern, tag in pii_patterns:
            for m in pattern.finditer(text):
                matched = m.group().strip()
                if matched and len(matched) > 1:
                    redact_texts.add(matched)
                    all_logs.append(f"[page{page_num}] {tag}: {matched[:60]}")

        # 후보자 이름 매칭
        if candidate and candidate.get("full_name"):
            for variant in _name_variants(candidate["full_name"]):
                if variant.lower() in text.lower():
                    redact_texts.add(variant)
                    all_logs.append(f"[page{page_num}] NAME: {variant}")

        # 위치 라벨 → 값만 redact (Korea 대체 텍스트 삽입)
        # 직장명 라벨 → 값만 redact
        # replacement_redacts: (target_text, replacement_text) — 대체 텍스트 삽입용
        replacement_redacts = []

        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            s_lower = stripped.lower()

            # 위치: "Current Location: Seoul, South Korea" → redact → "Korea"
            for label in LOCATION_LABELS:
                pat = re.match(rf"({re.escape(label)}\s*:?\s*)(.+)", s_lower)
                if pat and _is_korea(pat.group(2)):
                    label_end = len(pat.group(1))
                    value_text = stripped[label_end:].strip()
                    if value_text:
                        replacement_redacts.append((value_text, "Korea"))
                        all_logs.append(f"[page{page_num}] LOC→Korea: {value_text[:40]}")

            # 직장명: "Current Employer: YBM Academy" → redact (빈 대체)
            for label in WORKPLACE_LABELS:
                pat = re.match(rf"({re.escape(label)}\s*:?\s*)(.+)", s_lower)
                if pat:
                    label_end = len(pat.group(1))
                    value_text = stripped[label_end:].strip()
                    if value_text:
                        redact_texts.add(value_text)
                        all_logs.append(f"[page{page_num}] WORK_REDACT: {value_text[:40]}")

        if dry:
            continue

        # Redact 적용 — 일반 (흰색 덮기)
        for target in redact_texts:
            instances = page.search_for(target)
            for rect in instances:
                page.add_redact_annot(rect, fill=(1, 1, 1))

        # Redact 적용 — 대체 텍스트 삽입 (위치→Korea)
        for target, replacement in replacement_redacts:
            instances = page.search_for(target)
            for rect in instances:
                page.add_redact_annot(
                    rect, text=replacement, fill=(1, 1, 1),
                    text_color=(0, 0, 0), fontsize=10,
                )

        if redact_texts or replacement_redacts:
            page.apply_redactions()

    # 번호 삽입 (첫 페이지 최상단)
    if not dry and len(doc) > 0:
        first_page = doc[0]
        # 페이지 상단에 번호 텍스트 삽입
        rect = fitz.Rect(50, 15, 300, 45)
        # 기존 내용 위에 흰 박스 → 번호 텍스트
        first_page.draw_rect(rect, color=None, fill=(1, 1, 1))
        first_page.insert_text(
            fitz.Point(50, 38),
            str(brj_number),
            fontsize=20,
            fontname="helv",
            color=(0, 0, 0),
        )

    return doc, all_logs


def _build_search_patterns(candidate: dict = None):
    """PDF redaction용 검색 패턴 목록 생성"""
    patterns = [
        (RE_EMAIL, "EMAIL"),
        (RE_LINKEDIN, "LINKEDIN"),
        (RE_KAKAO, "KAKAO"),
        (RE_SNS, "SNS"),
        (RE_URL, "URL"),
        (RE_PASSPORT, "PASSPORT"),
        (RE_KR_ADDRESS, "KR_ADDR"),
    ]

    # 전화번호는 별도 처리 (7자리+ 필터)
    re_phone_strict = re.compile(
        r"(?:\+?\d{1,3}[\s\-.]?)?\(?\d{2,4}\)?[\s\-.]?\d{3,4}[\s\-.]?\d{3,4}"
    )
    patterns.append((re_phone_strict, "PHONE"))

    # 후보자 DB 정보
    if candidate:
        for field in ("email", "mobile_phone", "kakaotalk"):
            val = candidate.get(field, "")
            if val and len(val) > 3:
                patterns.append((re.compile(re.escape(val), re.I), f"DB_{field.upper()}"))

    return patterns


# ══════════════════════════════════════════════════════
#  6. 파일 저장 + 백업 + 로그
# ══════════════════════════════════════════════════════

def backup_original(filepath: Path):
    """원본 → originals/ 복사"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"{ts}_{filepath.name}"
    shutil.copy2(str(filepath), str(dest))
    return dest


def save_log(filepath: Path, brj_number: int, logs: list[str]):
    """삭제 로그 저장"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"BRJ{brj_number}_{filepath.stem}.json"
    data = {
        "source": str(filepath),
        "brj_number": brj_number,
        "processed_at": datetime.now().isoformat(),
        "removals": logs,
        "total_removals": len(logs),
    }
    log_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return log_path


def auto_detect_candidate(filepath: Path):
    """파일명에서 강사번호 자동 감지"""
    stem = filepath.stem
    # 파일명에서 3-5자리 숫자 추출
    numbers = re.findall(r"(\d{3,5})", stem)
    for num_str in numbers:
        candidate = get_candidate(int(num_str))
        if candidate:
            return candidate
    return None


# ══════════════════════════════════════════════════════
#  7. CLI 명령어
# ══════════════════════════════════════════════════════

def cmd_process(args):
    """process 명령"""
    input_path = Path(args.input)
    output_dir = Path(args.output) if args.output else DEFAULT_OUTPUT
    brj_number = args.number
    dry = args.dry

    if not input_path.exists():
        print(f"[ERROR] Path not found: {input_path}")
        sys.exit(1)

    # 파일 목록
    if input_path.is_file():
        files = [input_path]
    else:
        files = sorted(
            f for f in input_path.iterdir()
            if f.suffix.lower() in (".docx", ".pdf")
            and not f.name.startswith("~")
            and not f.name.startswith(".")
        )

    if not files:
        print(f"[INFO] No .docx/.pdf files in {input_path}")
        return

    mode = "DRY RUN" if dry else "PROCESS"
    print(f"\n{'=' * 60}")
    print(f"  BRIDGE Document Processor v2.0  [{mode}]")
    print(f"  Input:  {input_path}")
    print(f"  Output: {output_dir}")
    print(f"  Files:  {len(files)}")
    print(f"{'=' * 60}\n")

    for filepath in files:
        print(f"[{mode}] {filepath.name}")

        # 번호 결정
        current_number = brj_number
        candidate = None

        if current_number:
            candidate = get_candidate(current_number)
            if candidate:
                print(f"  #{current_number} {candidate['full_name']}")
            else:
                print(f"  #{current_number} (DB에 없음)")
        else:
            candidate = auto_detect_candidate(filepath)
            if candidate:
                current_number = candidate["sheet_number"]
                print(f"  Auto: #{current_number} {candidate['full_name']}")
            else:
                nums = re.findall(r"(\d{3,5})", filepath.stem)
                if nums:
                    current_number = int(nums[0])
                    print(f"  Filename: #{current_number}")
                else:
                    print(f"  [SKIP] 번호 없음. --number N 사용")
                    continue

        try:
            ext = filepath.suffix.lower()

            if ext == ".docx":
                doc, logs = process_docx(filepath, current_number, candidate, dry)
            elif ext == ".pdf":
                doc, logs = process_pdf(filepath, current_number, candidate, dry)
            else:
                print(f"  [SKIP] 미지원: {ext}")
                continue

            # 로그 출력
            if logs:
                print(f"  PII {len(logs)}건 {'발견' if dry else '삭제'}:")
                for l in logs[:10]:
                    print(f"    - {l}")
                if len(logs) > 10:
                    print(f"    ... +{len(logs)-10}건")

            if dry:
                if ext == ".pdf":
                    doc.close()
                print(f"  [DRY] 미리보기 완료\n")
                continue

            # 백업
            backup = backup_original(filepath)
            print(f"  Backup: {backup.name}")

            # 저장
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"BRJ{current_number}_{filepath.stem}{ext}"
            out_path = output_dir / out_name

            if ext == ".docx":
                doc.save(str(out_path))
            elif ext == ".pdf":
                doc.save(str(out_path), garbage=4, deflate=True)
                doc.close()

            print(f"  Output: {out_path.name}")

            # 삭제 로그 저장
            if logs:
                log_path = save_log(filepath, current_number, logs)
                print(f"  Log: {log_path.name}")

            print(f"  [OK]\n")

        except Exception as e:
            print(f"  [ERROR] {e}\n")
            import traceback
            traceback.print_exc()

    print(f"{'=' * 60}")
    print(f"  Done! {output_dir}")
    print(f"{'=' * 60}")


def cmd_lookup(args):
    """lookup 명령"""
    results = lookup_candidate(args.query)
    if not results:
        print(f"[INFO] No results for: {args.query}")
        return

    print(f"\n  {'#':>5}  {'Name':<35}  {'Nationality':<12}  Email")
    print(f"  {'─'*5}  {'─'*35}  {'─'*12}  {'─'*25}")
    for sn, name, nat, email in results:
        print(f"  {sn or '?':>5}  {(name or '')[:35]:<35}  {(nat or '')[:12]:<12}  {email or ''}")
    print()


def cmd_batch(args):
    """batch 명령: incoming/ 폴더 전체 일괄 처리"""
    dry = args.dry
    incoming = INCOMING_DIR
    if not incoming.exists() or not any(incoming.iterdir()):
        print(f"[INFO] incoming/ 폴더가 비어 있습니다: {incoming}")
        print(f"  파일을 여기에 넣으세요: {incoming}")
        return

    files = sorted(
        f for f in incoming.iterdir()
        if f.suffix.lower() in (".docx", ".pdf")
        and not f.name.startswith("~")
        and not f.name.startswith(".")
    )

    if not files:
        print(f"[INFO] .docx/.pdf 파일 없음: {incoming}")
        return

    mode = "DRY RUN" if dry else "BATCH"
    print(f"\n{'=' * 60}")
    print(f"  BRIDGE Document Processor v2.1  [{mode}]")
    print(f"  Incoming: {incoming}")
    print(f"  Output:   {DEFAULT_OUTPUT}")
    print(f"  Files:    {len(files)}")
    print(f"{'=' * 60}\n")

    # 각 파일 처리 (auto_detect_candidate로 번호 자동 감지)
    class FakeArgs:
        pass
    fake = FakeArgs()
    fake.output = str(DEFAULT_OUTPUT)
    fake.dry = dry
    fake.number = None

    for filepath in files:
        fake.input = str(filepath)
        print(f"[{mode}] {filepath.name}")

        candidate = auto_detect_candidate(filepath)
        current_number = None

        if candidate:
            current_number = candidate["sheet_number"]
            print(f"  Auto: #{current_number} {candidate['full_name']}")
        else:
            nums = re.findall(r"(\d{3,5})", filepath.stem)
            if nums:
                current_number = int(nums[0])
                candidate = get_candidate(current_number)
                if candidate:
                    print(f"  Filename: #{current_number} {candidate['full_name']}")
                else:
                    print(f"  Filename: #{current_number} (DB에 없음)")
            else:
                print(f"  [SKIP] 파일명에 번호 없음. 파일명에 강사번호 포함 필요")
                continue

        try:
            ext = filepath.suffix.lower()
            if ext == ".docx":
                doc, logs = process_docx(filepath, current_number, candidate, dry)
            elif ext == ".pdf":
                doc, logs = process_pdf(filepath, current_number, candidate, dry)
            else:
                continue

            if logs:
                print(f"  PII {len(logs)}건 {'발견' if dry else '삭제'}:")
                for l in logs[:10]:
                    print(f"    - {l}")
                if len(logs) > 10:
                    print(f"    ... +{len(logs)-10}건")

            if dry:
                if ext == ".pdf":
                    doc.close()
                print(f"  [DRY] 미리보기 완료\n")
                continue

            backup = backup_original(filepath)
            print(f"  Backup: {backup.name}")

            DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
            out_name = f"BRJ{current_number}_{filepath.stem}{ext}"
            out_path = DEFAULT_OUTPUT / out_name

            if ext == ".docx":
                doc.save(str(out_path))
            elif ext == ".pdf":
                doc.save(str(out_path), garbage=4, deflate=True)
                doc.close()

            print(f"  Output: {out_path.name}")

            if logs:
                log_path = save_log(filepath, current_number, logs)
                print(f"  Log: {log_path.name}")

            # 처리 완료된 파일을 incoming에서 제거
            filepath.unlink()
            print(f"  [OK] (incoming에서 제거됨)\n")

        except Exception as e:
            print(f"  [ERROR] {e}\n")
            import traceback
            traceback.print_exc()

    print(f"{'=' * 60}")
    print(f"  Done! 결과: {DEFAULT_OUTPUT}")
    print(f"{'=' * 60}")


def cmd_download(args):
    """download 명령: S3에서 후보자 파일 다운로드"""
    number = args.number
    candidate = get_candidate(number)
    if not candidate:
        print(f"[ERROR] #{number} 후보자를 찾을 수 없습니다")
        return

    print(f"  #{number} {candidate['full_name']}")

    # bx.py로 AWS 자격증명 로드
    try:
        sys.path.insert(0, str(BASE_DIR / "tools"))
        from bx import load_to_env
        load_to_env()
    except Exception as e:
        print(f"[ERROR] AWS 자격증명 로드 실패: {e}")
        print(f"  bx.py set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_S3_BUCKET 필요")
        return

    import boto3

    bucket = os.environ.get("AWS_S3_BUCKET")
    region = os.environ.get("AWS_REGION", "ap-northeast-2")
    if not bucket:
        print("[ERROR] AWS_S3_BUCKET 환경변수 미설정")
        return

    s3 = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )

    # S3에서 후보자 관련 파일 검색 (prefix 패턴)
    prefixes_to_try = [
        f"candidates/cnd_{number}/",
        f"candidates/{number}/",
        f"resumes/{number}/",
    ]

    downloaded = []
    dest_dir = args.output or str(INCOMING_DIR)
    Path(dest_dir).mkdir(parents=True, exist_ok=True)

    for prefix in prefixes_to_try:
        try:
            response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            for obj in response.get("Contents", []):
                key = obj["Key"]
                ext = Path(key).suffix.lower()
                if ext not in (".pdf", ".docx", ".doc", ".hwp"):
                    continue

                filename = f"{number}_{Path(key).name}"
                dest = Path(dest_dir) / filename
                print(f"  Downloading: {key} -> {filename}")
                s3.download_file(bucket, key, str(dest))
                downloaded.append(dest)
        except Exception as e:
            # prefix가 없을 수 있음 → 조용히 넘김
            pass

    if downloaded:
        print(f"\n  {len(downloaded)}개 다운로드 완료 → {dest_dir}")
        if not args.no_process:
            print(f"\n  자동 처리 시작...")
            for f in downloaded:
                try:
                    ext = f.suffix.lower()
                    if ext == ".docx":
                        doc, logs = process_docx(f, number, candidate)
                    elif ext == ".pdf":
                        doc, logs = process_pdf(f, number, candidate)
                    else:
                        continue

                    backup_original(f)
                    DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
                    out_name = f"BRJ{number}_{f.stem}{ext}"
                    out_path = DEFAULT_OUTPUT / out_name

                    if ext == ".docx":
                        doc.save(str(out_path))
                    elif ext == ".pdf":
                        doc.save(str(out_path), garbage=4, deflate=True)
                        doc.close()

                    if logs:
                        save_log(f, number, logs)
                    print(f"  [OK] {out_path.name} (PII {len(logs)}건 삭제)")

                except Exception as e:
                    print(f"  [ERROR] {f.name}: {e}")
    else:
        print(f"  S3에서 파일을 찾을 수 없습니다")
        print(f"  수동으로 파일을 incoming/에 넣고 batch 명령 사용:")
        print(f"    python doc_processor.py batch")


def cmd_setup(_args=None):
    """setup 명령: 폴더 구조 생성 + 상태 확인"""
    dirs = [INCOMING_DIR, DEFAULT_OUTPUT, BACKUP_DIR, LOG_DIR]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    print(f"\n  BRIDGE Document Processor v2.1 — 폴더 구조")
    print(f"  {'─' * 50}")
    print(f"  incoming/   : {INCOMING_DIR}")
    print(f"  processed/  : {DEFAULT_OUTPUT}")
    print(f"  originals/  : {BACKUP_DIR}")
    print(f"  logs/       : {LOG_DIR}")
    print()

    # incoming 파일 수
    incoming_files = [f for f in INCOMING_DIR.iterdir()
                      if f.suffix.lower() in (".docx", ".pdf")] if INCOMING_DIR.exists() else []
    processed_files = list(DEFAULT_OUTPUT.iterdir()) if DEFAULT_OUTPUT.exists() else []

    print(f"  대기 중: {len(incoming_files)}개")
    print(f"  처리됨: {len(processed_files)}개")

    if incoming_files:
        print(f"\n  대기 파일:")
        for f in incoming_files[:10]:
            print(f"    - {f.name}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="BRIDGE Document Processor v2.1 — PII 삭제 + 강사번호"
    )
    sub = parser.add_subparsers(dest="command")

    p_proc = sub.add_parser("process", help="단일 파일/폴더 처리")
    p_proc.add_argument("input", help="파일 또는 폴더")
    p_proc.add_argument("--number", "-n", type=int, help="강사번호")
    p_proc.add_argument("--output", "-o", help="출력 폴더")
    p_proc.add_argument("--dry", action="store_true", help="미리보기 (수정 없음)")

    p_batch = sub.add_parser("batch", help="incoming/ 폴더 일괄 처리")
    p_batch.add_argument("--dry", action="store_true", help="미리보기 (수정 없음)")

    p_dl = sub.add_parser("download", help="S3에서 후보자 파일 다운로드 + 처리")
    p_dl.add_argument("number", type=int, help="강사번호")
    p_dl.add_argument("--output", "-o", help="다운로드 폴더 (기본: incoming/)")
    p_dl.add_argument("--no-process", action="store_true", help="다운로드만 (처리 안 함)")

    p_look = sub.add_parser("lookup", help="후보자 검색")
    p_look.add_argument("query", help="이름 또는 이메일")

    sub.add_parser("setup", help="폴더 구조 생성 + 상태 확인")

    args = parser.parse_args()
    if args.command == "process":
        cmd_process(args)
    elif args.command == "batch":
        cmd_batch(args)
    elif args.command == "download":
        cmd_download(args)
    elif args.command == "lookup":
        cmd_lookup(args)
    elif args.command == "setup":
        cmd_setup(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
