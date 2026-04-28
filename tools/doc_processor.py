"""
BRIDGE Document Processor v2.6
후보자 이력서/커버레터에서 PII 삭제 + 강사번호 입력

사용법:
  python doc_processor.py setup                              # 폴더 구조 확인
  python doc_processor.py batch [--dry]                      # incoming/ 일괄 처리
  python doc_processor.py process <파일> --number 3057       # 단일 파일 처리
  python doc_processor.py download 3057                      # S3 다운로드+처리
  python doc_processor.py lookup "이름 또는 이메일"            # 후보자 검색
  python doc_processor.py init-db                            # file_uploads 테이블 생성

워크플로우:
  1) incoming/ 폴더에 파일 넣기 (파일명에 강사번호 포함: 3057_resume.pdf)
  2) batch --dry  → 미리보기 확인
  3) batch        → 처리 실행 (processed/ 에 결과, originals/ 에 원본 백업)
  4) 처리 완료 파일은 file_uploads 테이블에 자동 기록 (이력 추적)

지원 형식: .docx (서식 보존), .pdf (인-플레이스 redaction)
Python: "Q:/Phtyon 3/python.exe"
의존성: python-docx, PyMuPDF (fitz), python-dotenv, cryptography, boto3(S3용)
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
        "mobile_phone, kakaotalk, current_location, dob, gender, "
        "candidate_id, photo_url "
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
        "dob": _try_decrypt(row[7]) if row[7] else "",
        "gender": _try_decrypt(row[8]) if row[8] else "",
        "candidate_id": row[9] or "",
        "photo_url": row[10] or "",
    }


# 국적 영→한 매핑
_NAT_KR = {
    "american": "미국", "us": "미국", "usa": "미국", "united states": "미국",
    "british": "영국", "uk": "영국", "united kingdom": "영국", "english": "영국",
    "irish": "아일랜드", "ireland": "아일랜드", "n. ireland": "아일랜드",
    "northern irish": "아일랜드",
    "canadian": "캐나다", "canada": "캐나다",
    "australian": "호주", "australia": "호주",
    "new zealander": "뉴질랜드", "new zealand": "뉴질랜드", "kiwi": "뉴질랜드",
    "south african": "남아공", "south africa": "남아공",
    "filipino": "필리핀", "philippines": "필리핀",
    "indian": "인도", "india": "인도",
}

_GENDER_KR = {
    "male": "남성", "m": "남성", "남": "남성", "남성": "남성",
    "female": "여성", "f": "여성", "여": "여성", "여성": "여성",
}


def _extract_nationality_from_text(text: str) -> str:
    """
    이력서 텍스트에서 국적 추출.
    "Nationality: South African" → "south african"
    Returns 소문자 국적 문자열 or ""
    """
    # "Nationality: XXX" 패턴
    pat = re.compile(r"\bnationality\s*:?\s*([A-Za-z][A-Za-z\s]{2,30})", re.I)
    m = pat.search(text)
    if m:
        val = m.group(1).strip().lower()
        # 짧은 불필요 단어 제거
        for noise in ("unknown", "n/a", "na", "none", "other"):
            if val == noise:
                return ""
        return val
    # "Citizenship: XXX" 패턴 fallback
    pat2 = re.compile(r"\bcitizenship\s*:?\s*([A-Za-z][A-Za-z\s]{2,30})", re.I)
    m2 = pat2.search(text)
    if m2:
        return m2.group(1).strip().lower()
    return ""


def _update_candidate_nationality(sheet_number: int, nationality_raw: str):
    """DB의 nationality가 비어있거나 '미상'이면 추출된 값으로 업데이트"""
    if not nationality_raw or not sheet_number:
        return
    try:
        db = _get_db()
        row = db.execute(
            "SELECT nationality FROM candidates WHERE sheet_number = ?", (sheet_number,)
        ).fetchone()
        if not row:
            return
        current = (_try_decrypt(row[0]) or "").strip()
        # 비어있거나 "미상"인 경우에만 업데이트
        if current in ("", "미상", "unknown", "Unknown"):
            db.execute(
                "UPDATE candidates SET nationality = ? WHERE sheet_number = ?",
                (nationality_raw, sheet_number),
            )
            db.commit()
    except Exception:
        pass  # DB 업데이트 실패는 무시 (처리 계속)


def _is_cover_letter(filepath: Path) -> bool:
    """파일명으로 커버레터 여부 판별"""
    s = filepath.stem.lower()
    return any(kw in s for kw in (
        "cover letter", "coverletter", "cover_letter", "cl_", "cl ",
        "cl-", "커버레터", "커버", "자기소개",
    ))


def _merge_pdfs(cover_pdf: Path, resume_pdf: Path, output_pdf: Path):
    """커버레터 PDF + 이력서 PDF → 단일 PDF 병합"""
    import fitz
    merged = fitz.open()
    for src_path in [cover_pdf, resume_pdf]:
        if src_path and src_path.exists():
            src = fitz.open(str(src_path))
            merged.insert_pdf(src)
            src.close()
    merged.save(str(output_pdf), garbage=4, deflate=True)
    merged.close()


def _build_output_filename(number: int, candidate: dict = None, ext: str = ".docx") -> str:
    """
    파일명 단일 규격 (SSoT v2.0):
        {sheet_number}{국적}_{성별}({YY}born){ext}
    예: 5739영국_여성(00born).pdf / 6121아일랜드_남성(00born).pdf

    누락 요소는 폴백 문자열로 대체 (파일명 생성 100% 보장):
        국적 → "국적미상", 성별 → "성별미상", 생년 → "미상"

    호출 지점 (유일 SSoT — 다른 경로에서 파일명 직접 조합 금지):
      1) tools.doc_processor.process_docx / process_pdf
      2) api_server._auto_process_resume (자동 처리)
      3) api_server._fetch_processed_cv_attachment (메일 첨부)
      4) /api/admin/resume/preview/{id}
    """
    nat_kr = "국적미상"
    gender_kr = "성별미상"
    birth_yr = "미상"

    if candidate:
        nat_raw = (candidate.get("nationality") or "").strip().lower()
        if nat_raw:
            mapped = _NAT_KR.get(nat_raw)
            if mapped:
                nat_kr = mapped
            elif re.match(r"^[가-힣]+$", nat_raw):
                # 이미 한글 국적이 들어온 경우 (e.g. "미국")
                nat_kr = nat_raw[:6]

        gen_raw = (candidate.get("gender") or "").strip().lower()
        if gen_raw:
            mapped_g = _GENDER_KR.get(gen_raw)
            if mapped_g:
                gender_kr = mapped_g

        dob = (candidate.get("dob") or "").strip()
        if dob:
            yr_match = re.search(r"(19|20)(\d{2})", dob)
            if yr_match:
                birth_yr = yr_match.group(2)
            elif re.match(r"^\d{2}$", dob):
                birth_yr = dob

    # 규격: 항상 3요소 모두 포함 (누락 시 폴백 문자열)
    return f"{number}{nat_kr}_{gender_kr}({birth_yr}born){ext}"


# ── v2.0 전 파일타입 dispatcher ──────────────────────────────────────────
# 파일 확장자 → 처리 카테고리
_EXT_CATEGORY = {
    # PII 제거 대상 (PDF/워드)
    ".pdf":  "document",
    ".docx": "document",
    ".doc":  "document",
    ".rtf":  "document",
    ".odt":  "document",
    ".hwp":  "document",
    # 이미지 (PII 불필요)
    ".jpg":  "image",
    ".jpeg": "image",
    ".png":  "image",
    ".webp": "image",
    ".gif":  "image",
    ".bmp":  "image",
    ".tiff": "image",
    # 영상 (보관만)
    ".mp4":  "video",
    ".mov":  "video",
    ".avi":  "video",
    ".mkv":  "video",
    ".webm": "video",
    ".wmv":  "video",
    # 기타 (해시만)
}


def detect_file_category(filename: str) -> str:
    """파일 확장자로 카테고리 자동 판별.
    Returns: 'document' | 'image' | 'video' | 'other'
    """
    ext = Path(filename).suffix.lower()
    return _EXT_CATEGORY.get(ext, "other")


def process_file(
    filepath: Path,
    brj_number: int,
    candidate: dict = None,
    file_category: str = None,
    dry: bool = False,
    photo_path: Path = None,
):
    """
    v2.0 Universal file processor — 파일 타입에 따라 적절한 처리 라우팅.

    Returns: dict {
        "category": "document"|"image"|"video"|"other",
        "processed": bool,       # PII 제거 완료 여부
        "output_path": Path|None,# 처리 결과 저장 경로 (document만)
        "pii_count": int,        # 검출된 PII 수 (document만)
        "logs": list[str],
        "sha256": str|None,      # 출력 파일 무결성 해시
        "error": str|None,
    }
    """
    import hashlib as _hl

    if file_category is None:
        file_category = detect_file_category(filepath.name)

    result = {
        "category": file_category,
        "processed": False,
        "output_path": None,
        "pii_count": 0,
        "logs": [],
        "sha256": None,
        "error": None,
    }

    try:
        ext = filepath.suffix.lower()

        # ── DOCUMENT: PII 제거 (PDF/DOCX/DOC) ────────────────────────────
        if file_category == "document":
            if ext in (".docx", ".doc"):
                doc, logs = process_docx(
                    filepath, brj_number=brj_number, candidate=candidate,
                    dry=dry, photo_path=photo_path,
                )
                out_name = _build_output_filename(brj_number, candidate, ".docx")
                out_path = filepath.parent / out_name
                if not dry:
                    doc.save(str(out_path))
                    with open(out_path, "rb") as f:
                        result["sha256"] = _hl.sha256(f.read()).hexdigest()
                result["processed"] = True
                result["output_path"] = out_path
                result["logs"] = logs
                result["pii_count"] = sum(
                    1 for l in logs
                    if any(kw in l for kw in ("EMAIL:", "PHONE:", "NAME:", "LOCATION:", "WORKPLACE:"))
                )

            elif ext == ".pdf":
                out_path, logs = process_pdf(
                    filepath, brj_number=brj_number, candidate=candidate,
                    dry=dry, photo_path=photo_path,
                )
                if out_path and Path(out_path).exists():
                    with open(out_path, "rb") as f:
                        result["sha256"] = _hl.sha256(f.read()).hexdigest()
                result["processed"] = True
                result["output_path"] = Path(out_path) if out_path else None
                result["logs"] = logs
                result["pii_count"] = sum(
                    1 for l in logs
                    if any(kw in l for kw in ("EMAIL:", "PHONE:", "NAME:", "LOCATION:", "WORKPLACE:"))
                )

            else:
                # rtf/odt/hwp — PII 처리 모듈 없음 → pass-through
                with open(filepath, "rb") as f:
                    result["sha256"] = _hl.sha256(f.read()).hexdigest()
                result["processed"] = False
                result["output_path"] = filepath
                result["logs"] = [f"[SKIP] {ext} 포맷 PII 처리 미지원 — 원본 보존"]

        # ── IMAGE: 해시 + 크기 검증만 (PII 불필요) ───────────────────────
        elif file_category == "image":
            with open(filepath, "rb") as f:
                data = f.read()
                result["sha256"] = _hl.sha256(data).hexdigest()
            result["processed"] = True   # 처리 완료로 간주 (PII 없음)
            result["output_path"] = filepath
            result["logs"] = [f"[IMAGE] size={len(data)} sha256={result['sha256'][:16]}"]

        # ── VIDEO: 해시 + 메타데이터만 (변환/블러 미지원) ────────────────
        elif file_category == "video":
            with open(filepath, "rb") as f:
                data = f.read()
                result["sha256"] = _hl.sha256(data).hexdigest()
            result["processed"] = True
            result["output_path"] = filepath
            result["logs"] = [f"[VIDEO] size={len(data)} sha256={result['sha256'][:16]}"]

        # ── OTHER: 해시만 ─────────────────────────────────────────────────
        else:
            with open(filepath, "rb") as f:
                data = f.read()
                result["sha256"] = _hl.sha256(data).hexdigest()
            result["processed"] = True
            result["output_path"] = filepath
            result["logs"] = [f"[OTHER] ext={ext} size={len(data)} — 원본 보존"]

    except Exception as e:
        result["error"] = str(e)[:500]
        result["logs"].append(f"[ERROR] {type(e).__name__}: {e}")

    return result


def find_candidate_by_email(email: str):
    """이메일로 후보자 검색 → dict or None (정확 매칭 우선, 없으면 LIKE)"""
    db = _get_db()
    _COLS = ("sheet_number, full_name, nationality, email, "
             "mobile_phone, kakaotalk, current_location, dob, gender")
    # 정확 매칭
    row = db.execute(
        f"SELECT {_COLS} FROM candidates WHERE email = ? LIMIT 1",
        (email,),
    ).fetchone()
    if not row:
        # 암호화된 이메일일 수 있으므로 전체 스캔 (느리지만 정확)
        rows = db.execute(
            f"SELECT {_COLS} FROM candidates WHERE email IS NOT NULL AND email != ''"
        ).fetchall()
        for r in rows:
            decrypted = _try_decrypt(r[3])
            if decrypted and decrypted.lower() == email.lower():
                row = r
                break
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
        "dob": _try_decrypt(row[7]) if row[7] else "",
        "gender": _try_decrypt(row[8]) if row[8] else "",
    }


def _extract_emails_from_docx(filepath: Path) -> list[str]:
    """DOCX에서 이메일 주소 추출 (PII 삭제 전 원본에서)"""
    import docx
    doc = docx.Document(str(filepath))
    emails = set()
    all_text = []
    # 본문
    for p in doc.paragraphs:
        all_text.append(p.text)
    # 헤더/푸터
    for sec in doc.sections:
        if sec.header and sec.header.paragraphs:
            for p in sec.header.paragraphs:
                all_text.append(p.text)
        if sec.footer and sec.footer.paragraphs:
            for p in sec.footer.paragraphs:
                all_text.append(p.text)
    # 테이블
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    all_text.append(p.text)
    full = "\n".join(all_text)
    for m in RE_EMAIL.finditer(full):
        emails.add(m.group().lower())
    return list(emails)


# ══════════════════════════════════════════════════════
#  1b. file_uploads 테이블 (로컬 DB 이력 추적)
# ══════════════════════════════════════════════════════

_FILE_UPLOADS_DDL = """
CREATE TABLE IF NOT EXISTS file_uploads (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type   TEXT    NOT NULL DEFAULT 'candidate',
    entity_id     INTEGER,
    file_type     TEXT,
    file_url      TEXT,
    file_size     INTEGER DEFAULT 0,
    is_deleted    INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
)
"""


def _ensure_file_uploads_table():
    """file_uploads 테이블이 없으면 생성 (IF NOT EXISTS)."""
    db = _get_db()
    db.execute(_FILE_UPLOADS_DDL)
    db.commit()


def _record_file_upload(entity_id: int, file_type: str, file_url: str, file_size: int = 0):
    """처리 완료 파일을 file_uploads 테이블에 INSERT."""
    _ensure_file_uploads_table()
    db = _get_db()
    db.execute(
        "INSERT INTO file_uploads (entity_type, entity_id, file_type, file_url, file_size) "
        "VALUES (?, ?, ?, ?, ?)",
        ("candidate", entity_id, file_type, file_url, file_size),
    )
    db.commit()


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

# 한국 아파트/주거 주소 패턴 ("부영 1차 아파트", "래미안 빌라" 등)
RE_KR_RESIDENTIAL = re.compile(
    r"[가-힣]+(?:\s+[가-힣\d]+)*\s+(?:\d+차\s*)?(?:아파트|빌라|오피스텔|주공|맨션|타운하우스|연립)",
    re.UNICODE,
)

# 영문 주소 패턴: "123 Street Name, City, ST 12345"
# 전체 단어 + 약어(St./Ave./Dr. 등) 모두 매칭
RE_EN_ADDRESS = re.compile(
    r"\d{1,5}\s+[\w\s.]{3,40}\b(?:Street|Avenue|Boulevard|Drive|"
    r"Road|Lane|Court|Place|Trail|Circle|Parkway|Highway|"
    r"St\.?|Ave\.?|Blvd\.?|Dr\.?|Rd\.?|Ln\.?|Ct\.?|Pl\.?|Trl\.?|Cir\.?|Pkwy\.?|Hwy\.?)\b"
    r"[.,]?\s*(?:(?:Apt|Suite|Unit|#)\s*\w+[.,]?\s*)?"
    r"(?:\w[\w\s]*,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?)?",
    re.I,
)

# 한국 로마자 주소 패턴: "80-11, Jangji 1-gil," / "123 Teheran-ro" / "45 Sejong-daero"
RE_KR_ROMANIZED_ADDR = re.compile(
    r'\d+(?:[-–]\d+)?\s*,?\s*\w+(?:\s+\w+)?\s*\d*\s*[-–]?\s*'
    r'(?:gil|ro|daero|dong|gu|si|ri|myeon|eup|gun|do)\b'
    r'(?:\s*,\s*[\w\s]+)?',
    re.I,
)

# ── 학교/기관명 일반화 (전 세계 공통) ──────────────────────────────────────
# "Sheffield University", "Lincoln High School" → 기관 유형만 남김
RE_SCHOOL_NAMED = re.compile(
    r'\b[A-Z][a-zA-Z\'\-\.]+(?:\s+(?:of|the|at|and|&|[A-Z][a-zA-Z\'\-\.]+)){0,5}\s+'
    r'(?:University|College|High\s+School|Secondary\s+School|'
    r'Elementary\s+School|Primary\s+School|Grammar\s+School|'
    r'Boarding\s+School|Prep\s+School|Junior\s+School|'
    r'Sixth\s+Form\s+College|Collegiate|Polytechnic)\b'
)
# "University of Sheffield", "Institute of Technology" → 기관 유형만 남김
RE_UNIV_OF = re.compile(
    r'\b(?:University|Institute|College|School|Academy)\s+of\s+'
    r'[A-Z][a-zA-Z\s\'\-\.]{2,40}\b'
)

# 미국 도시+주: "Houston, TX", "New Orleans, Louisiana"
_US_STATES = (
    r'AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|'
    r'MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|'
    r'TX|UT|VT|VA|WA|WV|WI|WY|'
    r'Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|'
    r'Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|'
    r'Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|'
    r'Mississippi|Missouri|Montana|Nebraska|Nevada|New\s+Hampshire|'
    r'New\s+Jersey|New\s+Mexico|New\s+York|North\s+Carolina|North\s+Dakota|'
    r'Ohio|Oklahoma|Oregon|Pennsylvania|Rhode\s+Island|South\s+Carolina|'
    r'South\s+Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|'
    r'West\s+Virginia|Wisconsin|Wyoming'
)
RE_US_CITY_STATE = re.compile(
    r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?,\s*(?:' + _US_STATES + r')\b',
    re.I
)

# 외국 도시+국가: "Sheffield, United Kingdom", "Beijing, China"
RE_FOREIGN_CITY = re.compile(
    r'\b[A-Z][a-zA-Z\s\-]{2,30},\s*'
    r'(?:United\s+Kingdom|England|Scotland|Wales|Northern\s+Ireland|'
    r'China|Japan|Germany|France|South\s+Africa|Australia|New\s+Zealand|'
    r'Canada|USA|United\s+States(?:\s+of\s+America)?|Brazil|India|'
    r'Philippines|Zimbabwe|Zambia|Nigeria|Kenya|Ghana|Uganda)\b',
    re.I
)

# 한국 도시+국가 주소 패턴: "Gwangmyeong, South Korea", "Suwon, Korea"
# → 통째로 redact (주소줄 전체 삭제)
RE_KR_CITY_COUNTRY = re.compile(
    r'\b[A-Za-z][A-Za-z\s\-]{2,30},\s*(?:South\s+Korea|Korea|Republic\s+of\s+Korea)\b',
    re.I
)

# 나이 언급: "I am a 33 year old", "I'm a 34-year-old"
RE_AGE_MENTION = re.compile(
    r"\bI(?:'m|\s+am)\s+(?:a\s+)?\d{1,2}[\s\-]?year[\s\-]?old\b",
    re.I
)

# 비자 상태 공개: "E-2 VISA ELIGIBLE", "E2 visa holder"
RE_VISA_STATUS = re.compile(
    r'\b(?:E-?\d|F-?\d|H-?\d|G-?\d)\s*VISA\b(?:\s+(?:ELIGIBLE|HOLDER|STATUS|SPONSORSHIP))?\b',
    re.I
)

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
    # 경기도 주요 도시 (추가)
    "gwangmyeong", "uijeongbu", "gapyeong", "yeoju",
    "anseong", "pyeongtaek", "dongducheon", "gapyeong",
    # 기타 주요 시
    "mokpo", "chungju", "jecheon", "boryeong",
])

# PII 라벨 → 해당 줄 전체 삭제
# 주의: "line", "cell" 등 짧은 단어는 ":" 필수 조건으로 오탐 방지
PII_LINE_LABELS = [
    # 연락처 (colon 필수)
    ("email", True), ("e-mail", True),
    ("phone", True), ("telephone", True), ("mobile", True),
    ("cell", True), ("tel", True),
    ("korean telephone", True), ("u.k. telephone", True),
    ("uk telephone", True), ("us telephone", True),
    ("home phone", True), ("work phone", True), ("cell phone", True),
    ("contact", True), ("contact number", True),
    # 주소
    ("permanent address", True), ("home address", True),
    ("mailing address", True), ("address", True),
    ("current address", True),
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
    ("date of birth", True), ("dob", True),
    ("national id", True), ("ssn", True),
    # nationality/citizenship 은 고용주가 필요한 정보 → 삭제 안 함
    # ("nationality", True), ("citizenship", True),
    ("race", True), ("ethnicity", True), ("religion", True),
    ("birth", True), ("born", True),     # "Birth: UK / 1990"
    ("gender", True), ("sex", True),     # "Gender: Female"
    # 한국어
    ("이메일", True), ("전화", True), ("연락처", True),
    ("카카오", True), ("여권", True), ("주소", True),
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

# 한국 학원/학교 키워드 (경력줄에서 한국 근무지 감지용)
KR_WORKPLACE_KEYWORDS = frozenset([
    # 대형 프랜차이즈 / ESL 학원
    "ecc", "ybm", "pagoda", "avalon", "chungdahm", "cdl", "jle",
    "poly", "sle", "aclipse", "epik", "gepik", "smoe", "jlec",
    "slp", "rise", "cdi", "bcm", "gnb", "iei", "ael", "tel",
    "hess", "ewha", "top edu", "dada", "dadahak",
    "wonderland", "maple bear", "little america", "little fox",
    "english muse", "english plus", "emg education",
    "altiora", "bricks", "jungchul", "jeongchul",
    "sisa", "hansol", "daekyo", "kumon", "chungjae",
    "global adventure", "hampson", "engoo",
    "gse", "ils", "fastrackids", "ding ding dang", "seouldal",
    "reading town", "english channel", "yoon's", "eduplex",
    "chungdahm learning", "creverse", "lucid", "topia",
    "snb", "jls", "like english", "english egg",
    "canlearn", "kids college", "english town",
    # 추가 브랜드 (2026-04-28)
    "asset", "empire", "prairie think tool", "prairie",
    "gwanak", "yongsan-gu",
    # 일반 유형
    "english village", "language school", "language academy",
    "language institute", "language center", "language centre",
    "hagwon", "학원", "어학원", "영어학원", "유치원", "어린이집",
    "elementary school", "middle school", "high school",
    "primary school", "secondary school", "independent school",
    "grammar school", "boarding school", "prep school",
    "international school", "kindergarten", "preschool",
    "after-school", "afterschool", "after school",
    "private academy", "teaching academy", "english academy",
])

# 이미 일반 유형명인 KR_WORKPLACE_KEYWORDS 항목
# → 앞의 브랜드명만 제거하고 유형명 그대로 보존
# "Broad Language School" → "Language School" (not "English")
_GENERIC_SCHOOL_TYPES: dict = {
    "language school": "Language School",
    "language academy": "Language Academy",
    "language institute": "Language Institute",
    "language center": "Language Center",
    "language centre": "Language Centre",
    "english village": "English Village",
    "english academy": "English Academy",
    "teaching academy": "Teaching Academy",
    "private academy": "Private Academy",
    "international school": "International School",
    "elementary school": "Elementary School",
    "primary school": "Primary School",
    "secondary school": "Secondary School",
    "middle school": "Middle School",
    "high school": "High School",
    "kindergarten": "Kindergarten",
    "preschool": "Preschool",
    "after school": "After School",
    "after-school": "After-School",
    "afterschool": "Afterschool",
}
_GENERIC_TYPES_SET = frozenset(_GENERIC_SCHOOL_TYPES.keys())

# 브랜드 접두사 + 일반 유형명 → 유형명만 보존 (capture group 1 = generic type)
# "Broad Language School" → "Language School"
# !! 줄 경계 넘어 매칭 방지: [ \t]+ 사용 (not \s+) !!
_RE_KR_SCHOOL_PREFIX = re.compile(
    r'\b[A-Z][a-zA-Z\'\-\.]+(?:[ \t]+[A-Z][a-zA-Z\'\-\.]+){0,2}[ \t]+'
    r'(Language[ \t]+School|Language[ \t]+Academy|Language[ \t]+Institute|'
    r'Language[ \t]+Cent(?:er|re)|English[ \t]+(?:Village|Academy)|'
    r'Teaching[ \t]+Academy|Private[ \t]+Academy|International[ \t]+School|'
    r'(?:Elementary|Primary|Secondary|Middle|High)[ \t]+School|'
    r'Kindergarten|Preschool)\b',
    re.IGNORECASE,
)

# 이력서 섹션 헤더 (PDF 이름 추출 시 오탐 방지)
_RESUME_SECTION_HEADERS = frozenset({
    "professional summary", "work experience", "education", "references",
    "skills", "qualifications", "experience", "objective",
    "personal statement", "career summary", "career objective",
    "profile summary", "employment history", "work history",
    "professional experience", "relevant experience",
    "academic qualifications", "certifications", "teaching experience",
    "teaching history", "additional skills", "languages", "interests",
    "volunteer experience", "professional development", "awards",
    "curriculum vitae", "personal profile", "about me",
    "contact information", "contact details", "personal information",
    "personal details", "key skills", "core competencies",
    "summary of qualifications", "professional skills",
    "cover letter", "letter of introduction", "summary",
})

# 이름으로 오인하면 안 되는 단어 (파일명 + PDF 텍스트 양쪽 사용)
_NON_NAME_WORDS = frozenset({
    # CV/파일명 관련
    "resume", "cv", "curriculum", "vitae", "cover", "letter",
    "teaching", "teacher", "english", "esl", "tesol", "tefl",
    "application", "updated", "final", "new", "copy", "version",
    "document", "file", "scan", "draft", "official",
    # 주소/장소
    "street", "road", "avenue", "drive", "lane", "court", "place",
    "boulevard", "terrace", "close", "crescent", "way", "park",
    "phase", "block", "floor", "unit", "apt", "suite", "room",
    "north", "south", "east", "west",
    # 일반 영단어 (이름에는 없는)
    "and", "the", "for", "with", "from", "into", "about",
    "skills", "profile", "summary", "experience", "education",
})

# ── EDUCATION 섹션 보호용 헤더 감지 정규식 ──
# Pass 2.7(학교명 일반화)은 EDUCATION 섹션에서 실행 금지
_EDU_SECTION_RE = re.compile(
    r'^(?:education|academic\s+(?:qualifications?|background|history)|'
    r'educational\s+(?:background|history)|qualifications?|schooling)',
    re.IGNORECASE,
)
# 다른 섹션 헤더 감지 → EDUCATION 섹션 종료 신호
_OTHER_SECTION_RE = re.compile(
    r'^(?:experience|work(?:\s+(?:experience|history))?|employment(?:\s+history)?|'
    r'teaching(?:\s+experience)?|professional(?:\s+experience)?|'
    r'career(?:\s+(?:summary|objective))?|volunteer|internship|reference|'
    r'skills?|languages?|interests?|awards?|certifications?|'
    r'summary|objective|profile|about\s+me|personal)',
    re.IGNORECASE,
)

# 경력줄에서 한국 근무 상세 축약 패턴
# "YBM ECC, Uijeongbu, South Korea, March 2021 - Sept 2022" → "South Korea, March 2021 - Sept 2022"
# 날짜 패턴: "Jan 2021", "2021-2023", "March 2021 - Sept 2022", "2021 - Present"
_MONTH = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)
RE_DATE_RANGE = re.compile(
    r"(?:,\s*)?"
    r"(" + _MONTH + r"\.?\s*)?"
    r"(\d{4})"
    r"(?:\s*[-\u2013~]\s*"
    r"(?:" + _MONTH + r"\.?\s*)?"
    r"(?:\d{4}|[Pp]resent|[Cc]urrent)"
    r")?",
    re.I,
)


# ══════════════════════════════════════════════════════
#  3. PII 삭제 엔진
# ══════════════════════════════════════════════════════

def _is_korea(text: str) -> bool:
    lower = text.lower().strip()
    return any(kw in lower for kw in KR_KEYWORDS)


def _replace_workplace_generic(value: str) -> str:
    """
    근무처 명을 일반명으로 대체.
    - 영어 관련: "English"
    - 학원/아카데미: "Academy"
    - 대학: "University"
    """
    cleaned = value.strip()
    if not cleaned:
        return "English"

    # 기호 제거
    cleaned = re.sub(r"[!@#$%&*\-_~'\".,;():\[\]{}/?\\]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    lower = cleaned.lower()

    # 키워드 매칭 (우선순위 순)
    if any(kw in lower for kw in ["english", "esl", "language", "polyglot", "poly", "ybm", "ecc"]):
        return "English"
    if any(kw in lower for kw in ["academy", "hagwon", "cram", "institute", "school"]):
        return "Academy"
    if any(kw in lower for kw in ["university", "college"]):
        return "University"
    if any(kw in lower for kw in ["company", "corporation", "co", "ltd", "inc"]):
        return "Company"

    # 기본값
    return "English"


def _school_to_generic(match_text: str) -> str:
    """학교/기관명을 일반 유형명으로 대체."""
    lower = match_text.lower()
    if "university" in lower or "college" in lower or "polytechnic" in lower:
        return "University"
    return "School"


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


def remove_pii(text: str, candidate: dict = None, skip_school_names: bool = False) -> tuple[str, list[str]]:
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
        if len(digits) < 7:
            return m.group()
        # 연도 범위 오탐 방지: 모든 숫자 그룹이 연도(1900-2099)면 건너뜀
        # "2022-2023", "2017\n2021-2022", "2015-2020\n2017" 등 커버
        digit_groups = re.findall(r'\d+', m.group())
        if digit_groups and all(re.match(r'^(?:19|20)\d{2}$', g) for g in digit_groups):
            return m.group()
        log.append(f"PHONE: {m.group()[:40]}")
        return ""
    result = RE_PHONE.sub(phone_replacer, result)

    # 한국 주소 → "Korea"
    def addr_replacer(m):
        log.append(f"KR_ADDR→Korea: {m.group()[:40]}")
        return "Korea"
    result = RE_KR_ADDRESS.sub(addr_replacer, result)

    # 한국 아파트/주거 주소 삭제
    _sub(RE_KR_RESIDENTIAL, "", "KR_RESID")

    # 영문 주소 삭제 (거리+도시+주/zip)
    _sub(RE_EN_ADDRESS, "", "EN_ADDR")

    # 한국 로마자 주소 삭제 (80-11, Jangji 1-gil 등)
    _sub(RE_KR_ROMANIZED_ADDR, "", "KR_ROMAN_ADDR")

    # ── Pass 2.5: 한국 도시명 처리 ──
    # "Daegu, South Korea" → "South Korea"
    # "Seoul" → ""
    for city in KR_KEYWORDS:
        if len(city) > 2 and city.lower() not in ("korea", "south korea", "rok"):
            # 단어 경계로 정확하게 매칭
            pat = re.compile(r"\b" + re.escape(city) + r"\b", re.IGNORECASE)
            if pat.search(result):
                log.append(f"KR_CITY→REMOVE: {city}")
                # 도시명 제거, 앞뒤 쉼표/공백 정리
                result = pat.sub("", result)
                result = re.sub(r",\s*,", ",", result)
                result = re.sub(r"^\s*,\s*", "", result, flags=re.MULTILINE)
                result = re.sub(r"\s*,\s*$", "", result, flags=re.MULTILINE)
    # 도시 제거 후 남은 "— , Text" 패턴 정리: "— , South Korea" → "— South Korea"
    result = re.sub(r'([—–])\s*,+\s*', r'\1 ', result)
    result = re.sub(r',+\s*([—–])', r' \1', result)

    # ── Pass 2.6: 한국 업체명 처리 ──
    # Step 1: 브랜드 접두사 제거, 유형명 보존
    # "Broad Language School" → "Language School"
    def _school_prefix_replacer(m):
        canonical = " ".join(w.capitalize() for w in m.group(1).split())
        log.append(f"KR_SCHOOL_PREFIX→{canonical}: {m.group()[:60]}")
        return canonical
    result = _RE_KR_SCHOOL_PREFIX.sub(_school_prefix_replacer, result)

    # Step 2: 나머지 브랜드/업체명 → 일반명 대체
    # "YBM ECC" → "English", "POLY" → "English"
    # 이미 유형명인 항목(language school 등)은 Step 1에서 처리됐으므로 건너뜀
    for workplace in KR_WORKPLACE_KEYWORDS:
        if workplace in _GENERIC_TYPES_SET:
            continue  # 유형명 그대로 보존
        pat = re.compile(r"\b" + re.escape(workplace) + r"\b", re.IGNORECASE)
        if pat.search(result):
            generic = _replace_workplace_generic(workplace)
            log.append(f"KR_WORKPLACE→{generic}: {workplace}")
            result = pat.sub(generic, result)

    # ── Pass 2.7: 학교/기관명 일반화 ──
    # skip_school_names=True이면 건너뜀 (EDUCATION 섹션 보호용)
    # "Sheffield University" → "University", "Lincoln High School" → "School"
    def school_replacer(m):
        generic = _school_to_generic(m.group())
        log.append(f"SCHOOL→{generic}: {m.group()[:60]}")
        return generic
    if not skip_school_names:
        result = RE_SCHOOL_NAMED.sub(school_replacer, result)
        result = RE_UNIV_OF.sub(school_replacer, result)

    # ── Pass 2.8: 외국 도시/주 + 나이 + 비자 삭제 ──
    _sub(RE_US_CITY_STATE, "", "US_CITY_STATE")
    _sub(RE_FOREIGN_CITY, "", "FOREIGN_CITY")
    _sub(RE_AGE_MENTION, "", "AGE_MENTION")
    _sub(RE_VISA_STATUS, "", "VISA_STATUS")

    # ── Pass 3: 후보자별 PII (DB에서 가져온 값) ──
    if candidate:
        name = candidate.get("full_name", "")
        if name:
            # 성(Last name)만 삭제 (이름/First name은 유지)
            words = name.strip().split()
            if len(words) >= 2:
                last_name = words[-1]
                first_name = " ".join(words[:-1])  # 성을 제외한 모든 단어

                # 성이 2글자 이상인 경우 삭제
                if len(last_name) >= 2:
                    # 방법 1: 전체 이름을 찾아 성만 제거
                    # "Jodie Dumas" → "Jodie"
                    full_name_pat = re.compile(r"\b" + re.escape(name) + r"\b", re.IGNORECASE)
                    matches = full_name_pat.findall(result)
                    if matches:
                        log.append(f"FULLNAME→{first_name}: {name}")
                        result = full_name_pat.sub(first_name, result)

                    # 방법 2: 성만 단어 경계로 삭제
                    last_name_pat = re.compile(r"\b" + re.escape(last_name) + r"\b", re.IGNORECASE)
                    matches = last_name_pat.findall(result)
                    if matches:
                        log.append(f"LASTNAME→DELETE: {last_name}")
                        result = last_name_pat.sub("", result)
                        # 앞뒤 공백 정리
                        result = re.sub(r"\s+", " ", result)

        # DB에서 가져온 이메일/전화/카카오도 직접 삭제
        for field in ("email", "mobile_phone", "kakaotalk"):
            val = candidate.get(field, "")
            if val and len(val) > 2:
                escaped = re.escape(val)
                if re.search(escaped, result, re.I):
                    log.append(f"DB_{field.upper()}: {val[:30]}")
                    result = re.sub(escaped, "", result, flags=re.I)

    # ── Pass 4: 위치/직장 라벨 값 처리 ──
    # 모든 줄을 검사하여 라벨을 포함하는 줄을 처리
    lines_final = result.split("\n")
    final_lines = []

    for line in lines_final:
        stripped = line.strip()
        modified = line
        found = False

        # LOCATION_LABELS 검사
        for label in LOCATION_LABELS:
            # "Location: Seoul" 또는 "location : seoul" 등 다양한 형식 대응
            label_pat = re.compile(
                r"(.*?)\b" + re.escape(label) + r"\s*:?\s*(.+)",
                re.IGNORECASE
            )
            m = label_pat.match(stripped)
            if m:
                prefix, value = m.group(1), m.group(2).strip()
                if _is_korea(value):
                    # 도시명 제거: "Daegu, South Korea" → "South Korea"
                    # KR_KEYWORDS의 도시명들을 모두 제거
                    cleaned_value = value
                    for city in KR_KEYWORDS:
                        if len(city) > 2:
                            city_pat = re.compile(r"\b" + re.escape(city) + r"\s*,?\s*", re.IGNORECASE)
                            cleaned_value = city_pat.sub("", cleaned_value).strip()

                    # 결과가 비면 "South Korea"로 설정
                    if not cleaned_value or cleaned_value.lower() == "south korea":
                        cleaned_value = "South Korea"

                    log.append(f"LOCATION→{cleaned_value}: {value[:40]}")
                    # 원래 라인 구조 유지
                    indent = len(line) - len(line.lstrip())
                    modified = " " * indent + stripped.replace(value, cleaned_value)
                    found = True
                    break

        if not found:
            # WORKPLACE_LABELS 검사
            for label in WORKPLACE_LABELS:
                label_pat = re.compile(
                    r"(.*?)\b" + re.escape(label) + r"\s*:?\s*(.+)",
                    re.IGNORECASE
                )
                m = label_pat.match(stripped)
                if m:
                    prefix, value = m.group(1), m.group(2).strip()
                    generic_value = _replace_workplace_generic(value)
                    log.append(f"WORKPLACE→{generic_value}: {value[:40]}")
                    indent = len(line) - len(line.lstrip())
                    modified = " " * indent + stripped.replace(value, generic_value)
                    found = True
                    break

        final_lines.append(modified)

    result = "\n".join(final_lines)

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


def _extract_names_from_filename(filepath: Path) -> list[str]:
    """파일명에서 사람 이름 추출. 'Resume-DoniaBland2026 (1) - Donia Bland.docx' → ['Donia Bland', ...]"""
    stem = filepath.stem
    # " - Name" 패턴 (가장 흔함)
    parts = re.split(r"\s*-\s*", stem)
    names = []
    for part in parts:
        # 숫자만/키워드만 제외
        clean = re.sub(r"\(\d+\)", "", part).strip()
        clean = re.sub(r"\d{4,}", "", clean).strip()
        if clean.lower() in ("resume", "cv", "cover letter", "coverletter", ""):
            continue
        # 이름이 아닌 단어 제거 (Teaching, CV, English 등)
        words = [w for w in clean.split()
                 if w and w.lower() not in _NON_NAME_WORDS and len(w) >= 2]
        if len(words) >= 2 and all(w[0].isupper() for w in words if w):
            name_clean = " ".join(words)
            names.append(name_clean)
            # 개별 단어도 추가 (3글자 이상, non-name 제외)
            for w in words:
                if len(w) >= 3 and w.lower() not in _NON_NAME_WORDS:
                    names.append(w)
    return names


def _find_photo_for_candidate(filepath: Path) -> Path | None:
    """incoming 폴더에서 같이 넣은 사진 파일 찾기 (JPG/PNG)"""
    incoming = filepath.parent
    photo_exts = {".jpg", ".jpeg", ".png"}
    # 1) 같은 번호로 시작하는 사진
    stem_numbers = re.findall(r"(\d{3,5})", filepath.stem)
    for f in incoming.iterdir():
        if f.suffix.lower() in photo_exts:
            for num in stem_numbers:
                if num in f.stem:
                    return f
    # 2) incoming에 사진이 1개만 있으면 그거
    photos = [f for f in incoming.iterdir() if f.suffix.lower() in photo_exts]
    if len(photos) == 1:
        return photos[0]
    # 3) processed_docs 폴더에서도 찾기
    proc_parent = incoming.parent
    for subdir in [proc_parent / "incoming", proc_parent]:
        if not subdir.exists():
            continue
        for f in subdir.iterdir():
            if f.suffix.lower() in photo_exts:
                for num in stem_numbers:
                    if num in f.stem:
                        return f
    return None


def process_docx(filepath: Path, brj_number: int, candidate: dict = None,
                 dry: bool = False, photo_path: Path = None):
    """DOCX 처리: PII 삭제 + 번호/사진 삽입. Returns (doc, log_entries)"""
    import docx
    from docx.shared import Pt, Inches, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = docx.Document(str(filepath))
    all_logs = []

    # 파일명에서 이름 추출 (DB 불일치 대비)
    filename_names = _extract_names_from_filename(filepath)

    # Reference 섹션 헤더 감지용
    _REF_HEADERS = frozenset({
        "references", "reference", "professional references",
        "references & recommendations", "references and recommendations",
        "referee", "referees", "character references",
    })
    _ref_active = [False]  # mutable flag (closure 공유)

    def _process_paragraphs(paragraphs, section_name="body"):
        _in_edu = [False]  # EDUCATION 섹션 플래그 (클로저용 리스트)

        for para in paragraphs:
            original = para.text
            if not original.strip():
                continue

            stripped_lower = original.strip().lower()

            # EDUCATION 섹션 추적 — 본인 학력은 학교명 보호
            if _EDU_SECTION_RE.match(stripped_lower):
                _in_edu[0] = True
            elif _in_edu[0] and _OTHER_SECTION_RE.match(stripped_lower):
                _in_edu[0] = False

            # Reference 섹션 헤더 감지 → 이후 전체 삭제
            if stripped_lower in _REF_HEADERS:
                _ref_active[0] = True
                all_logs.append(f"[{section_name}] REF_SECTION_START")
                if not dry:
                    for run in para.runs:
                        run.text = ""
                continue

            # 다음 주요 섹션 헤더가 나오면 Reference 종료
            if _ref_active[0] and stripped_lower in _RESUME_SECTION_HEADERS:
                _ref_active[0] = False

            # Reference 섹션 내 내용 전체 삭제
            if _ref_active[0]:
                all_logs.append(f"[{section_name}] REF_DEL: {original.strip()[:60]}")
                if not dry:
                    for run in para.runs:
                        run.text = ""
                continue

            cleaned, log = remove_pii(original, candidate, skip_school_names=_in_edu[0])
            # 파일명에서 추출한 이름도 삭제
            for fn_name in filename_names:
                pat = re.compile(re.escape(fn_name), re.I)
                if pat.search(cleaned):
                    log.append(f"FILENAME_NAME: {fn_name}")
                    cleaned = pat.sub("", cleaned)
            if cleaned != original:
                all_logs.extend([f"[{section_name}] {l}" for l in log])
                if not dry:
                    # South Korea → 볼드 처리
                    if "South Korea" in cleaned:
                        _replace_with_bold_korea(para, cleaned)
                    else:
                        _replace_in_runs(para, cleaned)
                    # 하이퍼링크/필드코드 등 runs에 안 잡히는 요소 강제 클리어
                    if not cleaned.strip() and para.text.strip():
                        from docx.oxml.ns import qn
                        for child in list(para._element):
                            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                            if tag in ("hyperlink", "r", "fldSimple", "smartTag"):
                                para._element.remove(child)

    # 헤더/푸터 — 전체 삭제 (이름/주소/연락처 모두 비움)
    def _clean_header_footer(paragraphs, section_name="header"):
        for para in paragraphs:
            original = para.text
            if not original.strip():
                continue
            all_logs.append(f"[{section_name}] HDR_CLEAR: {original.strip()[:60]}")
            if not dry:
                for run in para.runs:
                    run.text = ""

    # ── 사전 처리: PII 삭제 전 국적 추출 → DB 업데이트 ──
    if not dry and candidate:
        _full_text = "\n".join(p.text for p in doc.paragraphs)
        _nat_extracted = _extract_nationality_from_text(_full_text)
        if _nat_extracted:
            _current_nat = (candidate.get("nationality") or "").strip()
            if _current_nat in ("", "미상", "unknown", "Unknown"):
                candidate["nationality"] = _nat_extracted
                _update_candidate_nationality(
                    candidate.get("sheet_number", 0), _nat_extracted
                )
                all_logs.append(f"[pre] NAT_EXTRACTED: {_nat_extracted}")

    # 본문
    _process_paragraphs(doc.paragraphs, "body")

    # 테이블
    for ti, table in enumerate(doc.tables):
        for row in table.rows:
            for cell in row.cells:
                _process_paragraphs(cell.paragraphs, f"table{ti}")

    # 헤더/푸터 — 전체 삭제
    for si, section in enumerate(doc.sections):
        for hf_name, hf in [("header", section.header), ("footer", section.footer)]:
            if hf and hf.paragraphs:
                _clean_header_footer(hf.paragraphs, f"{hf_name}{si}")
        try:
            fph = section.first_page_header
            if fph and fph.paragraphs:
                _clean_header_footer(fph.paragraphs, f"first_header{si}")
        except Exception:
            pass
        try:
            fpf = section.first_page_footer
            if fpf and fpf.paragraphs:
                _clean_header_footer(fpf.paragraphs, f"first_footer{si}")
        except Exception:
            pass

    # 문서 메타데이터 클리어 (이름/제목 제거)
    try:
        cp = doc.core_properties
        cp.title = ""
        cp.author = ""
        cp.subject = ""
        cp.keywords = ""
        cp.comments = ""
        cp.last_modified_by = ""
    except Exception:
        pass

    # 번호 + 사진 삽입 (최상단)
    if not dry:
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement

        photo = photo_path or _find_photo_for_candidate(filepath)
        body = doc.element.body

        # 기존 본문 이미지 모두 제거 (프로필 사진 중복 방지)
        for drawing in body.findall('.//' + qn('w:drawing')):
            parent = drawing.getparent()
            if parent is not None:
                parent.remove(drawing)
                all_logs.append("[photo] 기존 이미지 제거")
        for pict in body.findall('.//' + qn('w:pict')):
            parent = pict.getparent()
            if parent is not None:
                parent.remove(pict)

        # 1행 2열 테이블: [번호 | 사진]
        tbl = doc.add_table(rows=1, cols=2)
        tbl.autofit = True
        # 테두리 없음
        tbl_pr = tbl._element.tblPr
        borders = tbl_pr.find(qn("w:tblBorders"))
        if borders is not None:
            tbl_pr.remove(borders)

        # 왼쪽: 번호 (크고 굵게)
        left_cell = tbl.cell(0, 0)
        left_cell.text = ""
        p_num = left_cell.paragraphs[0]
        run_num = p_num.add_run(str(brj_number))
        run_num.bold = True
        run_num.font.size = Pt(28)
        run_num.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

        # 오른쪽: 사진
        right_cell = tbl.cell(0, 1)
        right_cell.text = ""
        p_photo = right_cell.paragraphs[0]
        p_photo.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if photo and photo.exists():
            run_photo = p_photo.add_run()
            run_photo.add_picture(str(photo), height=Cm(3.5))
            all_logs.append(f"[photo] 삽입: {photo.name}")
        else:
            all_logs.append("[photo] 사진 없음 (스킵)")

        # body의 맨 앞 자식 앞에 삽입 (테이블/단락 무관하게 최상단)
        first_child = body[0] if len(body) > 0 else None
        if first_child is not None:
            first_child.addprevious(tbl._element)
        else:
            body.append(tbl._element)

    return doc, all_logs


def _replace_with_bold_korea(para, cleaned_text: str):
    """South Korea를 볼드로 처리하여 단락에 삽입"""
    from docx.shared import Pt, RGBColor
    # 기존 runs의 서식 복사용 (첫 run의 font 정보 보존)
    base_font_size = None
    if para.runs:
        base_font_size = para.runs[0].font.size
    # 기존 runs 텍스트 비우기
    for run in para.runs:
        run.text = ""
    # South Korea 기준으로 분할하여 새 run 추가
    parts = cleaned_text.split("South Korea")
    for i, part in enumerate(parts):
        if part:
            run = para.add_run(part)
            if base_font_size:
                run.font.size = base_font_size
        if i < len(parts) - 1:
            kr_run = para.add_run("South Korea")
            kr_run.bold = True
            kr_run.font.size = base_font_size or Pt(11)
            kr_run.font.color.rgb = RGBColor(0, 0, 0)


# ══════════════════════════════════════════════════════
#  5. PDF 처리 (인-플레이스 redaction)
# ══════════════════════════════════════════════════════

def process_pdf(filepath: Path, brj_number: int, candidate: dict = None,
                dry: bool = False, photo_path: Path = None):
    """
    PDF 처리: PyMuPDF redaction으로 PII를 흰색 사각형으로 덮기.
    첫 페이지 상단 영역은 화이트아웃 후 번호+사진 삽입.
    Returns (doc, log_entries)
    """
    import fitz

    doc = fitz.open(str(filepath))
    all_logs = []

    # ── 사전 처리: PII 삭제 전 국적 추출 → DB 업데이트 ──
    if not dry and candidate:
        _pdf_full_text = "".join(page.get_text() for page in doc)
        _nat_extracted = _extract_nationality_from_text(_pdf_full_text)
        if _nat_extracted:
            _current_nat = (candidate.get("nationality") or "").strip()
            if _current_nat in ("", "미상", "unknown", "Unknown"):
                candidate["nationality"] = _nat_extracted
                _update_candidate_nationality(
                    candidate.get("sheet_number", 0), _nat_extracted
                )
                all_logs.append(f"[pre] NAT_EXTRACTED: {_nat_extracted}")

    # 모든 PII 패턴을 수집
    pii_patterns = _build_search_patterns(candidate)

    # 파일명에서 이름 추출 (DB 불일치 대비)
    filename_names = _extract_names_from_filename(filepath)

    # PDF 첫 페이지 텍스트에서 이름 추출 (상단 영역)
    _pdf_extracted_names = []
    if len(doc) > 0:
        first_text = doc[0].get_text()
        first_lines = [l.strip() for l in first_text.split("\n") if l.strip()]
        for line in first_lines[:5]:  # 상위 5줄만
            # 이름 패턴: 2~5단어, 각 첫글자 대문자, 짧은 줄
            if len(line) < 60 and not _should_skip_line(line.lower()):
                # 섹션 헤더 제외 (PROFESSIONAL SUMMARY 등)
                if line.strip().lower() in _RESUME_SECTION_HEADERS:
                    continue
                # ALL-CAPS 2+단어 → 섹션 제목으로 간주 (이름은 보통 Mixed Case)
                # 단, 2단어이고 각 단어가 짧으면(≤8자) 성씨일 가능성 → 개별 추가
                if line.isupper() and len(line.split()) >= 2:
                    _caps_words = line.split()
                    if len(_caps_words) == 2 and all(len(w) <= 8 for w in _caps_words):
                        _pdf_extracted_names.append(line)  # "VAN ZYL" 전체
                        for _cw in _caps_words:
                            if len(_cw) >= 3:
                                _pdf_extracted_names.append(_cw)  # "VAN", "ZYL" 개별
                    continue
                words = line.split()
                # 주소/일반 단어 포함 줄은 이름이 아님 (Zama Zama Street, Phase 1 등)
                if any(w.lower() in _NON_NAME_WORDS for w in words):
                    continue
                if 2 <= len(words) <= 5 and all(
                    w[0].isupper() or w in ("de", "van", "von", "del", "K.", "K")
                    for w in words if w
                ):
                    _pdf_extracted_names.append(line)
                    for w in words:
                        if len(w) >= 3 and w[0].isupper() and w.lower() not in _NON_NAME_WORDS:
                            _pdf_extracted_names.append(w)

    # ── 헤더 페이지 자동 감지 (More About Me 인트로 페이지 스킵) ──
    # "More About Me" / "About Me" 같은 자기소개 페이지는 Page 0이지만
    # 실제 이력서 헤더(이름+연락처)는 다른 페이지일 수 있음
    _header_page_num = 0
    _MORE_ABOUT_RE = re.compile(
        r'^\s*(more\s+about|about\s+me|personal\s+profile|personal\s+statement'
        r'|my\s+profile|profile\s+summary)',
        re.I,
    )
    for _hpi, _hpg in enumerate(doc):
        _top_txt = _hpg.get_text("text", clip=fitz.Rect(0, 0, _hpg.rect.width, 280))
        _top_lower = _top_txt.lower().strip()
        if _MORE_ABOUT_RE.match(_top_lower):
            continue  # About Me 페이지 스킵
        # 이메일/전화 패턴이 상단에 있으면 이력서 헤더 페이지
        if re.search(r'@[a-zA-Z]|(?:\+?\d{1,3}[\s\-]?\(?\d{2,4}\)?[\s\-]?\d{3})', _top_txt):
            _header_page_num = _hpi
            break
        # 컬러 헤더 사각형(베이지 등)이 상단에 있으면 이력서 헤더 페이지
        for _drw in _hpg.get_drawings():
            _dfill = _drw.get("fill")
            _dr = _drw.get("rect", fitz.Rect())
            if (_dfill and _dfill not in ((1, 1, 1), (0, 0, 0))
                    and _dr.y0 < 30 and _dr.width > _hpg.rect.width * 0.4):
                _header_page_num = _hpi
                break
        else:
            continue
        break

    for page_num, page in enumerate(doc):
        text = page.get_text()

        # 줄 단위 PII 라벨 검사 → redact 대상 텍스트 수집
        redact_texts = set()
        replacement_redacts = []  # (원문, 대체텍스트) 쌍
        job_title_replaces: list = []  # 직업 타이틀줄 전체교체: (원문, 클린텍스트) — 갭 없이 제거

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
                if not matched or len(matched) <= 1:
                    continue
                # 전화번호 오탐 방지: 7자리 미만 또는 연도 범위 건너뜀
                if tag == "PHONE":
                    if len(re.sub(r'\D', '', matched)) < 7:
                        continue
                    _dg = re.findall(r'\d+', matched)
                    if _dg and all(re.match(r'^(?:19|20)\d{2}$', g) for g in _dg):
                        continue
                redact_texts.add(matched)
                all_logs.append(f"[page{page_num}] {tag}: {matched[:60]}")

        # ── 후보자 이름: 성만 삭제, 이름 유지 (DOCX와 동일 정책) ──
        if candidate and candidate.get("full_name"):
            name = candidate["full_name"].strip()
            words = name.split()
            if len(words) >= 2:
                last_name = words[-1]
                first_name = " ".join(words[:-1])
                text_lower = text.lower()
                # 풀네임 → 이름만 남기기 (replacement redact)
                if name.lower() in text_lower:
                    replacement_redacts.append((name, first_name))
                    all_logs.append(f"[page{page_num}] FULLNAME→{first_name}: {name}")
                # 성 단독 삭제 (풀네임 미검출 시에도 성은 반드시 제거)
                if len(last_name) >= 2 and last_name.lower() in text_lower:
                    redact_texts.add(last_name)
                    all_logs.append(f"[page{page_num}] LASTNAME: {last_name}")
                # ── CamelCase 성 분리: "VanZyl" → "Van Zyl" / "VAN ZYL" 대응 ──
                _cc_parts = re.findall(r'[A-Z][a-z]+|[A-Z]{2,}', last_name)
                if len(_cc_parts) > 1:
                    _spaced_ln = " ".join(_cc_parts)
                    if _spaced_ln.lower() in text_lower:
                        redact_texts.add(_spaced_ln)
                        all_logs.append(f"[page{page_num}] LASTNAME_SPACE: {_spaced_ln}")
                    for _cp in _cc_parts:
                        if len(_cp) >= 3 and _cp.lower() in text_lower:
                            redact_texts.add(_cp)
                            all_logs.append(f"[page{page_num}] LASTNAME_PART: {_cp}")
                # PDF가 이름을 \n으로 분리 저장하는 경우 대비
                if name.lower() not in text_lower:
                    for _line in text.split("\n"):
                        _ls = _line.strip()
                        if name.lower() in _ls.lower():
                            replacement_redacts.append((_ls if len(_ls) < len(name) + 10 else name, first_name))
                            all_logs.append(f"[page{page_num}] FULLNAME_LINE→{first_name}: {_ls[:50]}")

        # 파일명 기반 이름: 성만 redact (이름 유지)
        # 단일 단어 이름 중 다중 단어 이름의 첫 번째 단어(이름)는 redact 제외
        _fn_first_names = {
            fn_n.split()[0].lower()
            for fn_n in filename_names
            if len(fn_n.split()) >= 2
        }
        for fn_name in filename_names:
            fn_words = fn_name.split()
            if len(fn_words) >= 2:
                fn_last = fn_words[-1]
                fn_first = " ".join(fn_words[:-1])
                if fn_name.lower() in text.lower():
                    replacement_redacts.append((fn_name, fn_first))
                    all_logs.append(f"[page{page_num}] FILENAME_NAME→{fn_first}: {fn_name}")
                # 성(last name): 최소 3자 이상이어야 redact — "T", "K" 등 이니셜 제외
                if len(fn_last) >= 3 and fn_last.lower() in text.lower():
                    redact_texts.add(fn_last)
            elif (fn_name.lower() not in _fn_first_names
                  and len(fn_name) >= 3  # 이니셜 단독 방지
                  and fn_name.lower() in text.lower()):
                # 단일 단어가 이름(first name)이면 redact 금지 — 성(last name)만 허용
                redact_texts.add(fn_name)
                all_logs.append(f"[page{page_num}] FILENAME_NAME: {fn_name}")

        # PDF 텍스트에서 추출한 이름: 성만 redact
        for pdf_name in _pdf_extracted_names:
            pdf_words = pdf_name.split()
            if len(pdf_words) >= 2:
                pdf_last = pdf_words[-1]
                pdf_first = " ".join(pdf_words[:-1])
                if pdf_name.lower() in text.lower():
                    replacement_redacts.append((pdf_name, pdf_first))
                    all_logs.append(f"[page{page_num}] PDF_NAME→{pdf_first}: {pdf_name}")
                if pdf_last.lower() in text.lower():
                    redact_texts.add(pdf_last)
            elif len(pdf_name) >= 3 and pdf_name.lower() in text.lower():
                redact_texts.add(pdf_name)
                all_logs.append(f"[page{page_num}] PDF_NAME: {pdf_name}")

        # ── 한국 학원명/도시명 redact ──
        page_lower = text.lower()
        # page_has_korea: KR_KEYWORDS 중 하나라도 있으면 True
        # (기존 좁은 regex 대신 전체 키워드 집합으로 확장 → Gyeonggi 등 오탐 방지)
        page_has_korea = any(kw in page_lower for kw in KR_KEYWORDS)

        keep_keywords = {"korea", "south korea", "rok", "republic of korea", "한국"}

        # ── 사전 계산: EDUCATION 섹션 줄 인덱스 ──
        # EDUCATION 섹션 줄에는 RE_SCHOOL_NAMED/KR_WORKPLACE 미적용 (본인 학력 보호)
        _page_lines = text.split("\n")
        _edu_lines: set = set()
        _edu_flag = False
        for _idx, _ll in enumerate(_page_lines):
            _ll_s = _ll.strip().lower()
            if _ll_s and _EDU_SECTION_RE.match(_ll_s):
                _edu_flag = True
            elif _edu_flag and _ll_s and _OTHER_SECTION_RE.match(_ll_s):
                _edu_flag = False
            if _edu_flag:
                _edu_lines.add(_idx)

        # ── 한국 학원명/도시명 redact ──
        # KR_WORKPLACE_KEYWORDS: EDUCATION 섹션 제외, 유형명(_GENERIC_TYPES_SET) 건너뜀
        for _idx, line in enumerate(_page_lines):
            stripped = line.strip()
            if not stripped or _idx in _edu_lines:
                continue
            s_lower = stripped.lower()
            has_kr = any(kw in s_lower for kw in KR_KEYWORDS)
            has_kr_work = any(kw in s_lower for kw in KR_WORKPLACE_KEYWORDS
                              if kw not in _GENERIC_TYPES_SET)

            # 브랜드 접두사 + 일반 유형명 → 유형명 보존 (replacement redact)
            # "Broad Language School" → "Language School"
            # !! 80자 초과 줄(서술문)은 제외 — "management for Kindergarten" 오탐 방지
            if len(stripped) <= 80:
                for m in _RE_KR_SCHOOL_PREFIX.finditer(stripped):
                    canonical = " ".join(w.capitalize() for w in m.group(1).split())
                    replacement_redacts.append((m.group(), canonical))
                    all_logs.append(f"[page{page_num}] KR_SCHOOL_PREFIX→{canonical}: {m.group()[:60]}")

            # 학원명 redact: 같은 줄에 한국 키워드 있거나, 짧은 줄(<50자)
            # 유형명(language school 등)은 건너뜀 — 위에서 처리
            _is_job_line_kw = " — " in stripped or " - " in stripped  # 직업 타이틀줄
            if has_kr_work:
                if _is_job_line_kw:
                    # 직업 타이틀줄: 갭 없이 제거 → 전체 줄 교체 방식 (job_title_replaces)
                    # (redact_texts에 추가하지 않음 — 아래 full-line clean 섹션에서 처리)
                    _cleaned_jt = stripped
                    # 1순위: Branch 전체 패턴 (Gwanak Branch 등) — KW 개별 제거 전에 먼저 처리
                    _cleaned_jt = re.sub(r'\b[A-Za-z]+(?:\s+[A-Za-z]+)?\s+Branch\b', '', _cleaned_jt, flags=re.I)
                    # 2순위: 괄호 위치 태그: (Yongsan-Gu SMU Camp)
                    _cleaned_jt = re.sub(
                        r'\s*\([^)]{3,50}(?:Gu|Branch|Camp|District|Center|Centre|City)\b[^)]*\)',
                        '', _cleaned_jt, flags=re.I)
                    # 3순위: KW 브랜드명 (긴 것 먼저)
                    _sorted_kws = sorted(
                        (kw for kw in KR_WORKPLACE_KEYWORDS if kw not in _GENERIC_TYPES_SET and kw in s_lower),
                        key=len, reverse=True
                    )
                    for _kw in _sorted_kws:
                        _cleaned_jt = re.sub(r'\b' + re.escape(_kw) + r'\b', '', _cleaned_jt, flags=re.I)
                    # 연속 공백 정리
                    _cleaned_jt = re.sub(r'[ \t]{2,}', ' ', _cleaned_jt).strip()
                    # "Junior -  — Teacher" → "Junior - Teacher" (branch 제거 후 dangling — 정리)
                    _cleaned_jt = re.sub(r'\s+-\s+—\s+', ' - ', _cleaned_jt)
                    # 앞뒤 고립 " - " 또는 " — " 정리
                    _cleaned_jt = re.sub(r'^[\s\-—]+', '', _cleaned_jt).strip()
                    if _cleaned_jt != stripped:
                        job_title_replaces.append((stripped, _cleaned_jt))
                        all_logs.append(f"[page{page_num}] JOB_TITLE_CLEAN: {stripped[:50]} → {_cleaned_jt[:50]}")
            # 직업 타이틀줄 중 KR_WORKPLACE 없어도 괄호/브랜치 있는 경우 처리
            # (Sookmyung Women's University — Teacher (Yongsan-Gu Camp) 같은 경우)
            if _is_job_line_kw and not has_kr_work:
                _paren_re = re.compile(
                    r'\s*\([^)]{3,50}(?:Gu|Branch|Camp|District|Center|Centre|City)\b[^)]*\)', re.I)
                _branch_re = re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+Branch\b')
                _cleaned_np = stripped
                _cleaned_np = _paren_re.sub('', _cleaned_np)
                _cleaned_np = _branch_re.sub('', _cleaned_np)
                _cleaned_np = re.sub(r'[ \t]{2,}', ' ', _cleaned_np).strip()
                if _cleaned_np != stripped:
                    job_title_replaces.append((stripped, _cleaned_np))
                    all_logs.append(f"[page{page_num}] JOB_PAREN_CLEAN: {stripped[:50]} → {_cleaned_np[:50]}")
            # ── 직업 타이틀줄 후처리: 대학교 고용주 + 한국인 이름형 브랜드 ──────
            # 위 두 블록 이후 실행 — has_kr_work 무관
            # 대상: "Sookmyung Women's University — Teacher" / "Min-Byung-Chul Junior - Teacher"
            if _is_job_line_kw:
                # 현재 job_title_replaces에서 이 줄의 최신 클린 텍스트 가져오기
                _current_clean_jt = next(
                    (_c for _o, _c in job_title_replaces if _o == stripped), stripped)
                _cleaned_jt2 = _current_clean_jt
                # 4순위: 고용주 대학교명 제거
                # "Sookmyung Women's University — Native English Teacher" → "Native English Teacher"
                _cleaned_jt2 = re.sub(
                    r'^.+?University\s*(?:—|-)\s*', '', _cleaned_jt2, flags=re.I).strip()
                # 5순위: 한국인 이름형 학원 브랜드 (Min-Byung-Chul Junior)
                # 패턴: 대문자+소문자 대시 연결 3단어 + 선택적 Junior/Senior
                _cleaned_jt2 = re.sub(
                    r'\b[A-Z][a-z]+-[A-Z][a-z]+-[A-Z][a-z]+(?:\s+(?:Junior|Senior|Academy|Institute))?\b',
                    '', _cleaned_jt2).strip()
                # 앞뒤 고립 구분자 정리
                _cleaned_jt2 = re.sub(r'^[\s\-—]+', '', _cleaned_jt2).strip()
                _cleaned_jt2 = re.sub(r'[ \t]{2,}', ' ', _cleaned_jt2).strip()
                if _cleaned_jt2 != stripped:
                    _existing_idx = next(
                        (i for i, (o, _) in enumerate(job_title_replaces) if o == stripped), -1)
                    if _existing_idx >= 0:
                        job_title_replaces[_existing_idx] = (stripped, _cleaned_jt2)
                    else:
                        job_title_replaces.append((stripped, _cleaned_jt2))
                    all_logs.append(
                        f"[page{page_num}] JOB_EXTRA_CLEAN: {stripped[:50]} → {_cleaned_jt2[:50]}")

            # 비직업타이틀 학원명: 한국 키워드 있거나 짧은 줄일 때만 redact
            if has_kr_work and not _is_job_line_kw and (has_kr or len(stripped) < 50):
                if len(stripped) < 50 and not has_kr:
                    redact_texts.add(stripped)
                    all_logs.append(f"[page{page_num}] KR_INST_LINE: {stripped[:60]}")
                for kw in KR_WORKPLACE_KEYWORDS:
                    if kw in _GENERIC_TYPES_SET:
                        continue  # 유형명 유지
                    kw_pat = re.compile(r"\b" + re.escape(kw) + r"\b", re.I)
                    for m in kw_pat.finditer(stripped):
                        redact_texts.add(m.group())
                        all_logs.append(f"[page{page_num}] KR_ACADEMY: {m.group()}")

            # 한국 도시명 redact (korea 자체는 유지) — page_has_korea일 때만
            # !! 학원/학교명 포함 줄은 도시명 유지
            #    "English Academy, Seoul" → Seoul 살림 (사용자 요구)
            #    독립 주소줄 "Gwangmyeong, South Korea" → RE_KR_CITY_COUNTRY로 처리
            if page_has_korea and has_kr and not has_kr_work:
                for city in KR_KEYWORDS:
                    if len(city) <= 2 or city.lower() in keep_keywords:
                        continue
                    city_pat = re.compile(r"\b" + re.escape(city) + r"\b", re.I)
                    for m in city_pat.finditer(stripped):
                        redact_texts.add(m.group())
                        all_logs.append(f"[page{page_num}] KR_CITY: {m.group()}")

        # ── 학교/기관명 일반화 + 외국 도시/나이/비자 — 줄 단위 스캔 ──
        # EDUCATION 섹션 줄 + 직업 타이틀줄(" — " 포함)은 RE_SCHOOL_NAMED 미적용
        # → 고용주 대학명(Sookmyung Women's University — Teacher) 보호
        for _idx, _line in enumerate(_page_lines):
            _ls = _line.strip()
            if not _ls:
                continue
            _is_job_title_line = " — " in _ls or " - " in _ls and any(
                w in _ls.lower() for w in ("teacher", "tutor", "instructor", "manager", "scholar")
            )
            # RE_SCHOOL_NAMED / RE_UNIV_OF — PDF에서는 비활성화
            # 학교명은 PII가 아님 (위치만 제거; RE_US_CITY_STATE / RE_FOREIGN_CITY 처리)
            # 고용주 대학명(Sookmyung Women's University — Teacher) 보호
            # if _idx not in _edu_lines and not _is_job_title_line:
            #     for m in RE_SCHOOL_NAMED.finditer(_ls): ...
            pass
            # 직업 타이틀줄 위치/괄호 태그는 job_title_replaces에서 일괄 처리 (위)
            # (JOB_PAREN_LOC / JOB_BRANCH → job_title_replaces 방식으로 통합, 갭 없이 제거)
            # 외국 도시/주 → blank redact
            for m in RE_US_CITY_STATE.finditer(_ls):
                redact_texts.add(m.group())
                all_logs.append(f"[page{page_num}] US_CITY: {m.group()[:40]}")
            for m in RE_FOREIGN_CITY.finditer(_ls):
                redact_texts.add(m.group())
                all_logs.append(f"[page{page_num}] FOREIGN_CITY: {m.group()[:40]}")
            # 나이/비자 → blank redact
            for m in RE_AGE_MENTION.finditer(_ls):
                redact_texts.add(m.group())
                all_logs.append(f"[page{page_num}] AGE: {m.group()[:40]}")
            for m in RE_VISA_STATUS.finditer(_ls):
                redact_texts.add(m.group())
                all_logs.append(f"[page{page_num}] VISA: {m.group()[:40]}")
            # 한국 도시+국가 주소줄: "Gwangmyeong, South Korea" → blank redact
            for m in RE_KR_CITY_COUNTRY.finditer(_ls):
                redact_texts.add(m.group())
                all_logs.append(f"[page{page_num}] KR_CITY_COUNTRY: {m.group()[:40]}")

        # 위치 라벨 → 값만 redact (Korea 대체 텍스트 삽입)
        # 직장명 라벨 → 값만 redact

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

        # ── Supplementary: get_text("dict") 기반 정밀 redact ──
        # 이유: search_for()는 다중 스팬 줄(Bold+Normal 혼합), 사이드바 레이아웃에서 실패 가능
        # 해결: 각 라인/스팬의 실제 bbox를 직접 사용해 추가 whiteout
        _pdict = page.get_text("dict", flags=0)
        _has_extra = False
        for _blk in _pdict.get("blocks", []):
            if _blk.get("type") != 0:
                continue
            for _lnobj in _blk.get("lines", []):
                _lspans = _lnobj.get("spans", [])
                _ltxt = "".join(s.get("text", "") for s in _lspans)
                _lstripped = _ltxt.strip()
                if not _lstripped:
                    continue
                # PII 라벨 줄 → 전체 라인 bbox whiteout (Bold: "Citizenship:" + Normal: " English" 같은 경우)
                if _should_skip_line(_lstripped.lower()):
                    page.add_redact_annot(fitz.Rect(_lnobj["bbox"]), fill=(1, 1, 1))
                    _has_extra = True
                    all_logs.append(f"[page{page_num}] LINE_BBOX: {_lstripped[:60]}")
                    continue
                # 스팬 단위 이메일/전화 (사이드바/컬럼 레이아웃에서 search_for 실패 보완)
                _ltxt_lower = _lstripped.lower()
                _line_has_kr = any(kw in _ltxt_lower for kw in KR_KEYWORDS)
                _line_has_kr_work = any(kw in _ltxt_lower for kw in KR_WORKPLACE_KEYWORDS
                                        if kw not in _GENERIC_TYPES_SET)
                for _span in _lspans:
                    _st = _span.get("text", "")
                    if not _st or len(_st) < 4:
                        continue
                    _sr = fitz.Rect(_span["bbox"])
                    if RE_EMAIL.search(_st):
                        page.add_redact_annot(_sr, fill=(1, 1, 1))
                        _has_extra = True
                        all_logs.append(f"[page{page_num}] EMAIL_BBOX: {_st[:60]}")
                    elif (RE_PHONE.search(_st) and len(re.sub(r"\D", "", _st)) >= 7
                          and not all(re.match(r'^(?:19|20)\d{2}$', g) for g in re.findall(r'\d+', _st))):
                        page.add_redact_annot(_sr, fill=(1, 1, 1))
                        _has_extra = True
                        all_logs.append(f"[page{page_num}] PHONE_BBOX: {_st[:60]}")
                    # 아이콘 폰트 글리프 삭제 (FontAwesome/icomoon — U+E000~U+F8FF Private Use Area)
                    # 순수 아이콘 스팬만 (공백 제외 모든 문자가 PUA 범위) — 헤더 상단 400px 이내
                    _is_pure_glyph = (
                        bool(_st.strip())
                        and all(0xE000 <= ord(c) <= 0xF8FF or c.isspace() for c in _st)
                    )
                    if _is_pure_glyph:
                        _span_y0 = _span["bbox"][1]
                        if _span_y0 < 400:
                            page.add_redact_annot(_sr, fill=(1, 1, 1))
                            _has_extra = True
                            all_logs.append(f"[page{page_num}] ICON_GLYPH y={_span_y0:.0f}: {repr(_st[:8])}")
                # 한국 학원명 라인 보충 bbox 처리 (search_for Bold/Normal 혼합 실패 보완)
                # 전체 라인에 학원 키워드 + 한국 키워드 있을 때 → 브랜드 접두어 스팬 whiteout
                if _line_has_kr_work and (_line_has_kr or len(_lstripped) < 60):
                    for _m in _RE_KR_SCHOOL_PREFIX.finditer(_lstripped):
                        # prefix 부분(match 에서 capture group 1 앞부분) 을 span 단위로 삭제
                        _prefix_txt = _lstripped[:_m.start(1)].strip()  # "JLS " 부분
                        if _prefix_txt:
                            for _sp2 in _lspans:
                                _sp2_t = _sp2.get("text", "").strip()
                                if not _sp2_t:
                                    continue
                                # 멀티스팬: "JLS" 스팬이 prefix에 포함되는 경우 (Bold/Normal 분리)
                                if _sp2_t.lower() in _prefix_txt.lower():
                                    page.add_redact_annot(fitz.Rect(_sp2["bbox"]), fill=(1, 1, 1))
                                    _has_extra = True
                                    all_logs.append(f"[page{page_num}] KR_BRAND_BBOX: {_sp2_t[:30]}")
                                # 싱글스팬: 스팬 안에 prefix가 포함된 경우 → search_for로 정밀 위치
                                elif (len(_lspans) == 1 and _prefix_txt.lower() in _sp2_t.lower()):
                                    for _prf_rect in page.search_for(
                                            _prefix_txt, clip=fitz.Rect(_sp2["bbox"])):
                                        page.add_redact_annot(_prf_rect, fill=(1, 1, 1))
                                        _has_extra = True
                                        all_logs.append(
                                            f"[page{page_num}] KR_BRAND_SINGLE: {_prefix_txt[:30]}"
                                        )
                    # 한국 도시명 스팬 삭제 — 학원명 포함 줄은 도시명 유지
                    # "English Academy, Seoul" → Seoul 살림 (사용자 요구)
                    # (도시 삭제는 독립 주소줄에만 적용)
                # 주소줄 bbox: "Gwangmyeong, South Korea" → 라인 전체 삭제
                if RE_KR_CITY_COUNTRY.search(_lstripped):
                    page.add_redact_annot(fitz.Rect(_lnobj["bbox"]), fill=(1, 1, 1))
                    _has_extra = True
                    all_logs.append(f"[page{page_num}] KR_ADDR_BBOX: {_lstripped[:50]}")
        if _has_extra:
            page.apply_redactions()

        # ── 직업 타이틀줄 전체 교체 (갭 없이) ──────────────────────────────────
        # 브랜드명/지점명 제거: 개별 단어 whitebox 대신 줄 전체 교체 → 공백 갭 없음
        if not dry and job_title_replaces:
            import fitz as _fitz
            # 페이지에 내장된 폰트 참조명 감지 (F5=Bold, F4=Regular 등)
            # em-dash(U+2014) 지원: 내장 폰트 사용 시 정상 렌더링
            _pg_fonts = page.get_fonts()
            _jt_bold_ref = None
            _jt_reg_ref = None
            for _pgf in _pg_fonts:
                _pfbase = _pgf[3].lower()  # basefont name
                _pfref = _pgf[4]           # /F-name in resource dict
                if "bold" in _pfbase:
                    _jt_bold_ref = _pfref
                elif "italic" not in _pfbase and "oblique" not in _pfbase:
                    _jt_reg_ref = _pfref

            _jt_dict = page.get_text("dict", flags=0)
            for _orig_jt, _clean_jt in job_title_replaces:
                # 원문 줄을 get_text("dict")에서 찾기
                for _jblk in _jt_dict.get("blocks", []):
                    if _jblk.get("type") != 0:
                        continue
                    for _jln in _jblk.get("lines", []):
                        _jlt = "".join(s.get("text", "") for s in _jln.get("spans", [])).strip()
                        # 원문이 이 줄에 포함되어 있으면 교체
                        if _orig_jt not in _jlt:
                            continue
                        _jrect = _fitz.Rect(_jln["bbox"])
                        _jspans = _jln.get("spans", [])
                        _jfst = _jspans[0] if _jspans else {}
                        _jfsize = _jfst.get("size", 8)
                        _jfflags = _jfst.get("flags", 0)
                        _jcolor_i = _jfst.get("color", 0)
                        _jrgb = (
                            ((_jcolor_i >> 16) & 0xFF) / 255.0,
                            ((_jcolor_i >> 8) & 0xFF) / 255.0,
                            (_jcolor_i & 0xFF) / 255.0,
                        )
                        # 폰트: 내장 PDF 폰트 참조 우선 (em-dash 지원)
                        _is_bold = bool(_jfflags & 16)
                        _jfontref = (_jt_bold_ref if _is_bold else _jt_reg_ref)
                        _ins_kwargs = dict(fontsize=_jfsize, color=_jrgb)
                        if _jfontref:
                            _ins_kwargs["fontname"] = _jfontref  # PDF 내장 폰트
                        else:
                            _ins_kwargs["fontname"] = "tibo" if _is_bold else "tiro"
                        # 1. 전체 줄 whiteout
                        page.add_redact_annot(_jrect, fill=(1, 1, 1))
                        page.apply_redactions()
                        # 2. 클린 텍스트 재삽입 (baseline = bbox 하단)
                        _jx0, _jy0, _jx1, _jy1 = _jrect
                        page.insert_text(
                            _fitz.Point(_jx0, _jy1),
                            _clean_jt,
                            **_ins_kwargs,
                        )
                        # 3. 밑줄 (원본이 bold+underline인 경우)
                        if _jfflags & 4:  # bit 2 = underline
                            _ul_y = _jy1 + 0.5
                            page.draw_line(
                                _fitz.Point(_jx0, _ul_y),
                                _fitz.Point(_jx1, _ul_y),
                                color=_jrgb, width=0.5
                            )
                        all_logs.append(f"[page{page_num}] JOB_LINE_REINSERT: {_clean_jt[:60]}")
                        break  # 한 줄만 처리 후 다음 교체 항목으로

    # ── 헤더 페이지 연락처 스트립 정리 + 번호/사진 삽입 ──
    # _header_page_num: 위에서 자동 감지된 실제 이력서 헤더 페이지 번호
    # 전략: 베이지 헤더 배경색 감지 → 연락처 스트립을 같은 색으로 덮어 아이콘/PII 흔적 제거
    #       → 번호(왼쪽) + 사진(오른쪽) 삽입
    if not dry and len(doc) > 0:
        hdr_page = doc[_header_page_num]
        pw = hdr_page.rect.width

        # ── 헤더 배경색 + 높이 감지 ──────────────────────────────────────────
        # 실제 colored 사각형이 페이지 상단에 있을 때만 헤더로 인정
        # fill=(0,0,0)/(1,1,1) 제외, y0<50, width>40% 조건
        _hdr_fill_color = None   # None = 헤더 없음
        _hdr_bottom = 0
        for _drw in hdr_page.get_drawings():
            _dfill = _drw.get("fill")
            _dr = _drw.get("rect", fitz.Rect())
            if (_dfill and _dfill not in ((1, 1, 1), (0, 0, 0))
                    and _dr.y0 < 50 and _dr.width > pw * 0.4
                    and _dr.y1 > _hdr_bottom):
                _hdr_fill_color = _dfill
                _hdr_bottom = _dr.y1

        _has_real_header = _hdr_fill_color is not None and _hdr_bottom > 40

        if _has_real_header:
            # ── 실제 colored 헤더가 있는 경우 ─────────────────────────────
            # 구분선 Y 감지 (헤더 아래 얇은 수평선 = 연락처 스트립 하단)
            _divider_y = _hdr_bottom + 110  # fallback
            for _drw in hdr_page.get_drawings():
                _dr = _drw.get("rect", fitz.Rect())
                if (_dr.y0 > _hdr_bottom and (_dr.y1 - _dr.y0) < 3
                        and _dr.width > pw * 0.5 and _dr.y0 < _divider_y):
                    _divider_y = _dr.y0

            # ── 헤더 밝기 기반 커버 방식 결정 ────────────────────────────
            # 밝은 헤더(beige/tan, 0.5이상): 왼쪽 사진 플레이스홀더만 덮기 → 중앙 이름 보존 (6165형)
            # 어두운 헤더(navy/dark, 0.5미만): 전체 이름 영역 덮기 → 자간벌림/벡터 이름 제거 (6189형)
            _r, _g, _b = _hdr_fill_color
            _brightness = 0.299 * _r + 0.587 * _g + 0.114 * _b

            if _brightness >= 0.5:
                # 밝은 헤더 (6165형): 왼쪽 사진 플레이스홀더만 덮기
                _name_cover_right = pw * 0.34
                _cover_mode = "LEFT"
            else:
                # 어두운 헤더 (6189형): 이름 영역 전체 덮기
                photo_reserve = _hdr_bottom - 10
                _name_cover_right = pw - photo_reserve - 5
                _cover_mode = "FULL"

            hdr_page.draw_rect(
                fitz.Rect(0, 0, _name_cover_right, _hdr_bottom),
                color=None, fill=_hdr_fill_color,
            )
            all_logs.append(
                f"[page{_header_page_num}] HDR_COVER({_cover_mode}): 0-{_name_cover_right:.0f} / 0-{_hdr_bottom:.0f}"
            )

            # ② 연락처 스트립 화이트아웃 (헤더 하단 ~ 구분선)
            # 아이콘 박스(벡터) + PII 텍스트 완전 제거
            hdr_page.draw_rect(
                fitz.Rect(0, _hdr_bottom - 2, pw, _divider_y + 1),
                color=None, fill=(1, 1, 1),
            )
            all_logs.append(
                f"[page{_header_page_num}] STRIP_WHITE: y={_hdr_bottom:.0f}~{_divider_y:.0f}"
            )

            # ③ 강사 번호 삽입 (헤더 왼쪽)
            _num_y = _hdr_bottom * 0.70
            # 밝은 헤더 → 어두운 텍스트, 어두운 헤더 → 밝은 텍스트
            _r, _g, _b = _hdr_fill_color
            _brightness = 0.299 * _r + 0.587 * _g + 0.114 * _b
            _num_color = (0.95, 0.95, 0.95) if _brightness < 0.5 else (0.20, 0.14, 0.06)
            hdr_page.insert_text(
                fitz.Point(12, _num_y),
                str(brj_number),
                fontsize=24,
                fontname="helv",
                color=_num_color,
            )
            all_logs.append(f"[page{_header_page_num}] BRJNUM: {brj_number}")

            # ④ 사진 삽입 (헤더 오른쪽)
            photo = photo_path or _find_photo_for_candidate(filepath)
            if photo and photo.exists():
                _img_margin = 5
                _img_h = int(_hdr_bottom - _img_margin * 2)
                photo_rect = fitz.Rect(
                    pw - _img_h - _img_margin, _img_margin,
                    pw - _img_margin, _hdr_bottom - _img_margin,
                )
                try:
                    hdr_page.insert_image(photo_rect, filename=str(photo))
                    all_logs.append(f"[photo] {_header_page_num}p {_img_h}px: {photo.name}")
                except Exception as e:
                    all_logs.append(f"[photo] 삽입 실패: {e}")
            else:
                all_logs.append("[photo] 없음 (스킵)")

        else:
            # ── 헤더 없는 일반 CV ─────────────────────────────────────────
            # beige/dark rect를 그리지 않음 — 레이아웃 보존
            # 강사 번호만 페이지 상단 왼쪽에 작게 삽입
            hdr_page.insert_text(
                fitz.Point(10, 20),
                str(brj_number),
                fontsize=14,
                fontname="helv",
                color=(0.15, 0.15, 0.15),
            )
            all_logs.append(f"[page{_header_page_num}] NO_HDR BRJNUM: {brj_number}")

            # 사진 삽입 (있으면 페이지 우상단)
            photo = photo_path or _find_photo_for_candidate(filepath)
            if photo and photo.exists():
                _img_size = 90
                _img_margin = 10
                photo_rect = fitz.Rect(
                    pw - _img_size - _img_margin, _img_margin,
                    pw - _img_margin, _img_size + _img_margin,
                )
                try:
                    hdr_page.insert_image(photo_rect, filename=str(photo))
                    all_logs.append(f"[photo] NO_HDR {_header_page_num}p: {photo.name}")
                except Exception as e:
                    all_logs.append(f"[photo] 삽입 실패: {e}")

    # PDF 메타데이터 클리어 (이름/제목 제거)
    if not dry:
        doc.set_metadata({
            "title": "", "author": "", "subject": "",
            "keywords": "", "creator": "", "producer": "",
        })

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
        (RE_KR_RESIDENTIAL, "KR_RESID"),   # 부영 1차 아파트 등
        (RE_EN_ADDRESS, "EN_ADDR"),
        (RE_KR_ROMANIZED_ADDR, "KR_ROMAN_ADDR"),
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

def _convert_docx_to_pdf(docx_path: Path, pdf_path: Path, timeout: int = 60) -> bool:
    """DOCX → PDF 변환 (Word COM 자동화). 성공 시 True.
    timeout: Word COM 최대 대기 초 (기본 60초, 초과 시 강제 종료 후 False)
    """
    import threading as _thr

    def _word_com() -> bool:
        word = None
        try:
            import comtypes.client
            word = comtypes.client.CreateObject("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0   # wdAlertsNone — 보안/업데이트 팝업 차단
            doc = word.Documents.Open(
                str(docx_path.resolve()),
                ConfirmConversions=False,
                ReadOnly=True,
                AddToRecentFiles=False,
            )
            doc.SaveAs(str(pdf_path.resolve()), FileFormat=17)  # 17 = wdFormatPDF
            doc.Close(SaveChanges=False)
            return True
        except ImportError:
            return False
        except Exception as e:
            print(f"  [PDF WARN] COM 변환 실패: {e}")
            return False
        finally:
            if word is not None:
                try:
                    word.Quit(SaveChanges=False)
                except Exception:
                    pass

    result = [False]
    t = _thr.Thread(target=lambda: result.__setitem__(0, _word_com()), daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        print(f"  [PDF WARN] Word COM {timeout}초 타임아웃 — 강제 중단")
        # Word 프로세스 종료
        try:
            import subprocess
            subprocess.run(["taskkill", "/F", "/IM", "WINWORD.EXE"],
                           capture_output=True)
        except Exception:
            pass
        return False
    if result[0]:
        return True
    # fallback: LibreOffice
    try:
        import subprocess
        lo_paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        lo = next((p for p in lo_paths if Path(p).exists()), None)
        if lo:
            subprocess.run(
                [lo, "--headless", "--convert-to", "pdf",
                 "--outdir", str(pdf_path.parent), str(docx_path)],
                capture_output=True, timeout=60,
            )
            # LibreOffice는 원본 이름으로 저장하므로 rename
            lo_out = pdf_path.parent / (docx_path.stem + ".pdf")
            if lo_out.exists() and lo_out != pdf_path:
                lo_out.rename(pdf_path)
            return pdf_path.exists()
    except Exception as e:
        print(f"  [PDF WARN] LibreOffice 실패: {e}")
    print("  [PDF FAIL] PDF 변환 불가 — comtypes/docx2pdf/LibreOffice 모두 없음")
    print("             pip install comtypes 또는 pip install docx2pdf 로 설치")
    return False


def backup_original(filepath: Path):
    """원본 → originals/ 복사"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"{ts}_{filepath.name}"
    shutil.copy2(str(filepath), str(dest))
    return dest


def save_log(filepath, brj_number: int, logs: list[str]):
    """삭제 로그 저장"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stem = filepath.stem if isinstance(filepath, Path) else str(filepath).replace("#", "")
    log_path = LOG_DIR / f"BRJ{brj_number}_{stem}.json"
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
    """파일명에서 강사번호 자동 감지 (이름/위치 교차 검증)"""
    stem = filepath.stem
    numbers = re.findall(r"(\d{3,5})", stem)
    for num_str in numbers:
        candidate = get_candidate(int(num_str))
        if not candidate:
            continue
        # 번호가 파일명 맨 앞이면 확실한 매칭 (예: "3060_resume.pdf")
        if stem.startswith(num_str):
            return candidate
        # _# 뒤에 오면 확실한 매칭 (예: "resume_3060.pdf", "#3060.pdf")
        if re.search(rf"[_#]{num_str}\b", stem):
            return candidate
        # 그 외: 후보자 이름이 파일명에 포함되는지 검증
        cand_name = (candidate.get("full_name") or "").lower()
        stem_lower = stem.lower()
        if cand_name:
            name_words = [w for w in cand_name.split() if len(w) >= 3]
            if any(w in stem_lower for w in name_words):
                return candidate
        # 이름 매칭 실패 → 우연한 숫자 (연도 2026 등) → 스킵
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
            out_name = _build_output_filename(current_number, candidate, ext)
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


def _resolve_candidate(filepath: Path) -> tuple[int | None, dict | None]:
    """파일에서 후보자 번호+정보 자동 탐지. Returns (number, candidate_dict)."""
    candidate = auto_detect_candidate(filepath)
    if candidate and candidate.get("sheet_number"):
        return candidate["sheet_number"], candidate

    # auto_detect_candidate가 이미 파일명 숫자를 이름 교차검증했으므로
    # 여기서 재시도 불필요 → 이메일 매칭으로 직행

    # 이메일 기반 매칭 (DOCX + PDF)
    emails = []
    ext = filepath.suffix.lower()
    try:
        if ext == ".docx":
            emails = _extract_emails_from_docx(filepath)
        elif ext == ".pdf":
            import fitz
            doc = fitz.open(str(filepath))
            for page in doc:
                for m in RE_EMAIL.finditer(page.get_text()):
                    emails.append(m.group().lower())
            doc.close()
    except Exception:
        pass
    for em in emails:
        cand = find_candidate_by_email(em)
        if cand:
            if cand.get("sheet_number"):
                return cand["sheet_number"], cand
            return None, cand
    return None, None


def _quick_extract_names(filepath: Path) -> set[str]:
    """문서에서 이름 빠르게 추출 (사진 매칭용). Returns lowercase name parts (3글자+)."""
    names = set()
    # 파일명 기반
    for fn_name in _extract_names_from_filename(filepath):
        names.update(w.lower().rstrip(".") for w in fn_name.split() if len(w) >= 3)
    # PDF 첫 페이지 텍스트 기반
    if filepath.suffix.lower() == ".pdf":
        try:
            import fitz
            doc = fitz.open(str(filepath))
            if len(doc) > 0:
                first_text = doc[0].get_text()
                for line in (l.strip() for l in first_text.split("\n") if l.strip()):
                    if len(line) >= 60:
                        continue
                    if line.strip().lower() in _RESUME_SECTION_HEADERS:
                        continue
                    if line.isupper() and len(line.split()) >= 2:
                        continue
                    if _should_skip_line(line.lower()):
                        continue
                    words = line.split()
                    if 2 <= len(words) <= 5 and all(
                        w[0].isupper() or w in ("de", "van", "von", "del", "K.", "K")
                        for w in words if w
                    ):
                        names.update(w.lower().rstrip(".") for w in words if len(w) >= 3)
                        break  # 첫 이름 줄만
            doc.close()
        except Exception:
            pass
    return names


def _extract_nationality_gender(filepath: Path) -> dict:
    """문서 텍스트에서 국적/성별 추출 (DB 없는 후보자용)."""
    text = ""
    ext = filepath.suffix.lower()
    try:
        if ext == ".pdf":
            import fitz
            doc = fitz.open(str(filepath))
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
        elif ext == ".docx":
            import docx
            doc = docx.Document(str(filepath))
            text = "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return {}

    info = {}
    text_lower = text.lower()

    # 국적 — 명시적 라벨 우선
    nat_line = re.search(
        r"(?:nationality|citizenship|country of (?:origin|birth))\s*:?\s*(.+)",
        text, re.I,
    )
    if nat_line:
        val = nat_line.group(1).strip().lower()
        for key in _NAT_KR:
            if key in val:
                info["nationality"] = key
                break
    # 라벨 없으면 본문에서 국가명 빈도 추론
    if "nationality" not in info:
        nat_hints = {
            "american": ["united states", "u.s.a", "u.s. citizen"],
            "british": ["united kingdom", "u.k.", "british citizen", "british national"],
            "irish": ["ireland", "irish citizen"],
            "canadian": ["canada", "canadian citizen"],
            "australian": ["australia", "australian citizen"],
            "south african": ["south africa"],
        }
        for nat, patterns in nat_hints.items():
            if any(p in text_lower for p in patterns):
                info["nationality"] = nat
                break

    # 성별 — 명시적 라벨 우선
    gender_line = re.search(
        r"(?:gender|sex)\s*:?\s*(male|female|m|f)\b", text, re.I,
    )
    if gender_line:
        val = gender_line.group(1).strip().lower()
        if val in ("male", "m"):
            info["gender"] = "male"
        elif val in ("female", "f"):
            info["gender"] = "female"

    # DOB — 라벨 패턴
    dob_match = re.search(
        r"(?:date\s+of\s+birth|d\.?o\.?b\.?|born|birth\s*date)\s*:?\s*"
        r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}|"
        r"\w+\s+\d{1,2},?\s+\d{4}|\d{4})",
        text, re.I,
    )
    if dob_match:
        info["dob"] = dob_match.group(1).strip()
    # DOB 없으면 고등학교 졸업년도로 출생년 추정 (졸업년 - 18)
    if "dob" not in info:
        hs_match = re.search(r"high\s+school.*?(\d{4})", text, re.I)
        if hs_match:
            grad_year = int(hs_match.group(1))
            if 2000 <= grad_year <= 2030:
                info["dob"] = str(grad_year - 18)

    return info


def cmd_batch(args):
    """batch 명령: incoming/ 폴더 전체 일괄 처리 (커버레터+이력서 자동 병합)"""
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

    # ── 파일 분류: 커버레터 vs 이력서 ──
    cover_letters = []
    resumes = []
    for f in files:
        if _is_cover_letter(f):
            cover_letters.append(f)
        else:
            resumes.append(f)

    # ── 사진 맵 수집 ──
    photo_map = {}
    for f in incoming.iterdir():
        if f.suffix.lower() in (".jpg", ".jpeg", ".png") and not f.name.startswith(("~", ".")):
            photo_map[f.stem.lower()] = f

    # ── 자동 번호 카운터 (충돌 방지) ──
    db = _get_db()
    _next_auto = (db.execute("SELECT MAX(sheet_number) FROM candidates").fetchone()[0] or 3000) + 1

    # ── 후보자별 그룹핑 ──
    groups = {}  # number → {resume, cover, candidate}

    for filepath in resumes:
        num, cand = _resolve_candidate(filepath)
        if not num:
            num = _next_auto
            _next_auto += 1
        groups[num] = {"resume": filepath, "cover": None, "candidate": cand}

    # 커버레터 매칭: 번호 → 파일명 이름 유사도 → 신규 그룹
    _stop_words = {"cover", "letter", "resume", "copy", "of", "the", "for"}
    for filepath in cover_letters:
        num, cand = _resolve_candidate(filepath)

        # 1) 번호 매칭
        if num and num in groups:
            groups[num]["cover"] = filepath
            if cand and not groups[num]["candidate"]:
                groups[num]["candidate"] = cand
            continue

        # 2) 파일명 이름 유사도 매칭 ("Cover letter - grace peers" ↔ "Copy of Resume - grace peers")
        cl_words = set(re.findall(r"[a-z]{3,}", filepath.stem.lower())) - _stop_words
        matched = False
        for gnum, grp in groups.items():
            if grp["resume"] and not grp["cover"]:
                res_words = set(re.findall(r"[a-z]{3,}", grp["resume"].stem.lower())) - _stop_words
                common = cl_words & res_words
                if len(common) >= 1:
                    groups[gnum]["cover"] = filepath
                    if cand and not grp["candidate"]:
                        grp["candidate"] = cand
                    print(f"  [MATCH] Cover ↔ Resume by name: {common}")
                    matched = True
                    break
        if matched:
            continue

        # 3) 신규 그룹
        if not num:
            num = _next_auto
            _next_auto += 1
        groups[num] = {"resume": None, "cover": filepath, "candidate": cand}

    total = len(groups)
    print(f"\n{'=' * 60}")
    print(f"  BRIDGE Document Processor v2.4  [{mode}]")
    print(f"  Incoming:  {incoming}")
    print(f"  Output:    {DEFAULT_OUTPUT}")
    print(f"  Resumes:   {len(resumes)} | Cover Letters: {len(cover_letters)}")
    print(f"  Groups:    {total}")
    print(f"{'=' * 60}\n")

    import tempfile

    for current_number, grp in groups.items():
        resume_path = grp["resume"]
        cover_path = grp["cover"]
        candidate = grp["candidate"]

        # DB 없는 후보자: 문서에서 국적/성별 추출 (파일명 생성용)
        if not candidate:
            doc_path = resume_path or cover_path
            if doc_path and doc_path.exists():
                extracted_info = _extract_nationality_gender(doc_path)
                if extracted_info:
                    candidate = extracted_info
                    print(f"  [INFO] 문서에서 추출: {extracted_info}")

        label = f"#{current_number}"
        if candidate:
            label += f" {candidate.get('full_name', '')}"
        print(f"[{mode}] {label}")
        if resume_path:
            print(f"  Resume: {resume_path.name}")
        if cover_path:
            print(f"  Cover:  {cover_path.name}")

        # 사진 매칭: 번호 → 이력서 파일명 유사도 → 이름 유사도
        photo = None
        for pk, pf in list(photo_map.items()):
            if str(current_number) in pk:
                photo = pf
                break
        if not photo and resume_path:
            res_stem = resume_path.stem.lower()
            for pk, pf in list(photo_map.items()):
                # 이력서 이니셜/이름과 사진 파일명 비교
                res_words = set(re.findall(r"[a-z]{2,}", res_stem))
                pk_words = set(re.findall(r"[a-z]{2,}", pk))
                if res_words & pk_words:
                    photo = pf
                    break
        if not photo and candidate and candidate.get("full_name"):
            name_parts = candidate["full_name"].lower().split()
            for pk, pf in list(photo_map.items()):
                if any(part in pk for part in name_parts if len(part) >= 3):
                    photo = pf
                    break
        # NEW: 문서 텍스트에서 추출한 이름으로 사진 매칭
        if not photo:
            doc_names = set()
            for doc_path in [resume_path, cover_path]:
                if doc_path and doc_path.exists():
                    doc_names |= _quick_extract_names(doc_path)
            if doc_names:
                for pk, pf in list(photo_map.items()):
                    pk_words = set(re.findall(r"[a-z]{3,}", pk))
                    common = pk_words & doc_names
                    if common:
                        photo = pf
                        print(f"  [MATCH] Photo ↔ Doc name: {common}")
                        break
        # 그룹 1개 + 사진 1개면 자동 매칭
        if not photo and len(groups) == 1 and len(photo_map) == 1:
            photo = next(iter(photo_map.values()))
        all_logs = []
        temp_pdfs = []  # (순서, pdf_path) — 최종 병합용

        try:
            # ── 커버레터 처리 ──
            if cover_path:
                ext = cover_path.suffix.lower()
                if ext == ".docx":
                    # 커버레터 DOCX: PII 제거 (번호/사진 삽입 안 함)
                    cl_doc, cl_logs = process_docx(
                        cover_path, current_number, candidate, dry, photo_path=None
                    )
                    all_logs.extend(cl_logs)
                    if not dry:
                        backup_original(cover_path)
                        # 임시 DOCX 저장 → PDF 변환
                        tmp_docx = Path(tempfile.mktemp(suffix=".docx"))
                        cl_doc.save(str(tmp_docx))
                        tmp_pdf = Path(tempfile.mktemp(suffix=".pdf"))
                        if _convert_docx_to_pdf(tmp_docx, tmp_pdf):
                            temp_pdfs.append(("cover", tmp_pdf))
                            tmp_docx.unlink()
                        else:
                            temp_pdfs.append(("cover_docx", tmp_docx))
                        cover_path.unlink()
                elif ext == ".pdf":
                    cl_doc, cl_logs = process_pdf(
                        cover_path, current_number, candidate, dry
                    )
                    all_logs.extend(cl_logs)
                    if not dry:
                        backup_original(cover_path)
                        tmp_pdf = Path(tempfile.mktemp(suffix=".pdf"))
                        cl_doc.save(str(tmp_pdf), garbage=4, deflate=True)
                        cl_doc.close()
                        temp_pdfs.append(("cover", tmp_pdf))
                        cover_path.unlink()

            # ── 이력서 처리 ──
            if resume_path:
                ext = resume_path.suffix.lower()
                if ext == ".docx":
                    doc, res_logs = process_docx(
                        resume_path, current_number, candidate, dry, photo_path=photo
                    )
                    all_logs.extend(res_logs)
                    if not dry:
                        backup_original(resume_path)
                        tmp_docx = Path(tempfile.mktemp(suffix=".docx"))
                        doc.save(str(tmp_docx))
                        tmp_pdf = Path(tempfile.mktemp(suffix=".pdf"))
                        if _convert_docx_to_pdf(tmp_docx, tmp_pdf):
                            temp_pdfs.append(("resume", tmp_pdf))
                            tmp_docx.unlink()
                        else:
                            temp_pdfs.append(("resume_docx", tmp_docx))
                        resume_path.unlink()
                elif ext == ".pdf":
                    doc, res_logs = process_pdf(
                        resume_path, current_number, candidate, dry,
                        photo_path=photo,
                    )
                    all_logs.extend(res_logs)
                    if not dry:
                        backup_original(resume_path)
                        tmp_pdf = Path(tempfile.mktemp(suffix=".pdf"))
                        doc.save(str(tmp_pdf), garbage=4, deflate=True)
                        doc.close()
                        temp_pdfs.append(("resume", tmp_pdf))
                        resume_path.unlink()

            # ── 로그 출력 ──
            if all_logs:
                print(f"  PII {len(all_logs)}건 {'발견' if dry else '삭제'}:")
                for l in all_logs[:10]:
                    print(f"    - {l}")
                if len(all_logs) > 10:
                    print(f"    ... +{len(all_logs)-10}건")

            if dry:
                print(f"  [DRY] 미리보기 완료\n")
                continue

            # ── 최종 PDF 병합/출력 ──
            DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
            final_name = _build_output_filename(current_number, candidate, ".pdf")
            final_path = DEFAULT_OUTPUT / final_name

            pdf_parts = [p for _, p in temp_pdfs if p.suffix == ".pdf"]
            if len(pdf_parts) >= 2:
                # 커버레터 + 이력서 PDF 병합
                cover_p = next((p for t, p in temp_pdfs if "cover" in t), None)
                resume_p = next((p for t, p in temp_pdfs if "resume" in t), None)
                _merge_pdfs(cover_p, resume_p, final_path)
                print(f"  Output: {final_name} (커버레터+이력서 병합 PDF)")
            elif len(pdf_parts) == 1:
                shutil.move(str(pdf_parts[0]), str(final_path))
                print(f"  Output: {final_name} (PDF)")
            else:
                # PDF 변환 실패 — DOCX 그대로 출력
                docx_parts = [p for _, p in temp_pdfs if p.suffix == ".docx"]
                if docx_parts:
                    final_path = DEFAULT_OUTPUT / _build_output_filename(
                        current_number, candidate, ".docx")
                    shutil.move(str(docx_parts[0]), str(final_path))
                    print(f"  Output: {final_path.name} (DOCX — PDF 변환 실패)")

            # 임시 파일 정리
            for _, tmp in temp_pdfs:
                if tmp.exists():
                    tmp.unlink()

            if all_logs:
                log_path = save_log(
                    resume_path or cover_path or Path(f"#{current_number}"),
                    current_number, all_logs,
                )
                print(f"  Log: {log_path.name}")

            # DB 기록
            try:
                file_size = final_path.stat().st_size if final_path.exists() else 0
                _record_file_upload(
                    entity_id=current_number,
                    file_type=final_path.suffix.lstrip("."),
                    file_url=str(final_path),
                    file_size=file_size,
                )
                print(f"  [DB] file_uploads 기록 완료")
            except Exception as db_err:
                print(f"  [DB WARN] 기록 실패 (무시): {db_err}")

            # 사진 사용 후 incoming에서 제거 (다음 batch 오염 방지)
            if photo and photo.exists() and photo.parent == incoming:
                backup_original(photo)
                photo.unlink()
                photo_map.pop(photo.stem.lower(), None)
                print(f"  [PHOTO] {photo.name} → originals/ 이동")

            print(f"  [OK]\n")

        except Exception as e:
            print(f"  [ERROR] {e}\n")
            import traceback
            traceback.print_exc()

    print(f"{'=' * 60}")
    print(f"  Done! 결과: {DEFAULT_OUTPUT}")
    print(f"{'=' * 60}")


def cmd_download(args):
    """download 명령: S3에서 후보자 이력서+사진 다운로드 → PII 삭제 → PDF 출력"""
    number = args.number
    candidate = get_candidate(number)
    if not candidate:
        print(f"[ERROR] #{number} 후보자를 찾을 수 없습니다")
        return

    cand_id = candidate.get("candidate_id", "")
    print(f"  #{number} {candidate['full_name']} (ID: {cand_id or 'N/A'})")

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

    # S3 경로: candidate_id 기반 (cnd_xxxx) + sheet_number 폴백
    prefixes_to_try = []
    if cand_id:
        prefixes_to_try.append(f"candidates/{cand_id}/")
    prefixes_to_try.extend([
        f"candidates/cnd_{number}/",
        f"candidates/{number}/",
        f"resumes/{number}/",
    ])

    _DOC_EXTS = {".pdf", ".docx", ".doc", ".hwp"}
    _IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
    downloaded_docs = []
    downloaded_photo = None
    dest_dir = args.output or str(INCOMING_DIR)
    Path(dest_dir).mkdir(parents=True, exist_ok=True)

    for prefix in prefixes_to_try:
        try:
            response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            for obj in response.get("Contents", []):
                key = obj["Key"]
                ext = Path(key).suffix.lower()
                s3_name = Path(key).name

                if ext in _DOC_EXTS:
                    filename = f"{number}_{s3_name}"
                    dest = Path(dest_dir) / filename
                    print(f"  [DOC] {key} → {filename}")
                    s3.download_file(bucket, key, str(dest))
                    downloaded_docs.append(dest)
                elif ext in _IMG_EXTS and not downloaded_photo:
                    # 사진: thumb 제외, 원본 우선
                    if "thumb" in s3_name.lower():
                        continue
                    filename = f"{number}_photo{ext}"
                    dest = Path(dest_dir) / filename
                    print(f"  [PHOTO] {key} → {filename}")
                    s3.download_file(bucket, key, str(dest))
                    downloaded_photo = dest
        except Exception:
            pass

    total = len(downloaded_docs) + (1 if downloaded_photo else 0)
    if total == 0:
        print(f"  S3에서 파일을 찾을 수 없습니다")
        print(f"  수동으로 파일을 incoming/에 넣고 batch 명령 사용:")
        print(f"    python doc_processor.py batch")
        return

    print(f"\n  {total}개 다운로드 완료 (문서 {len(downloaded_docs)}, 사진 {1 if downloaded_photo else 0})")

    if args.no_process:
        return

    # ── 자동 처리 ──
    import tempfile
    print(f"\n  자동 처리 시작...")
    temp_pdfs = []

    for f in downloaded_docs:
        try:
            ext = f.suffix.lower()
            is_cover = _is_cover_letter(f)

            if ext == ".docx":
                doc, logs = process_docx(
                    f, number, candidate, photo_path=None if is_cover else downloaded_photo)
            elif ext == ".pdf":
                doc, logs = process_pdf(
                    f, number, candidate, photo_path=None if is_cover else downloaded_photo)
            else:
                continue

            backup_original(f)

            if ext == ".docx":
                tmp_docx = Path(tempfile.mktemp(suffix=".docx"))
                doc.save(str(tmp_docx))
                tmp_pdf = Path(tempfile.mktemp(suffix=".pdf"))
                label = "cover" if is_cover else "resume"
                if _convert_docx_to_pdf(tmp_docx, tmp_pdf):
                    temp_pdfs.append((label, tmp_pdf))
                    tmp_docx.unlink()
                else:
                    temp_pdfs.append((f"{label}_docx", tmp_docx))
            elif ext == ".pdf":
                tmp_pdf = Path(tempfile.mktemp(suffix=".pdf"))
                doc.save(str(tmp_pdf), garbage=4, deflate=True)
                doc.close()
                label = "cover" if is_cover else "resume"
                temp_pdfs.append((label, tmp_pdf))

            f.unlink()
            if logs:
                save_log(f, number, logs)
            print(f"  PII {len(logs)}건 삭제: {f.name}")

        except Exception as e:
            print(f"  [ERROR] {f.name}: {e}")
            import traceback
            traceback.print_exc()

    # ── 최종 PDF 병합/출력 ──
    DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
    final_name = _build_output_filename(number, candidate, ".pdf")
    final_path = DEFAULT_OUTPUT / final_name

    pdf_parts = [p for _, p in temp_pdfs if p.suffix == ".pdf"]
    if len(pdf_parts) >= 2:
        cover_p = next((p for t, p in temp_pdfs if "cover" in t and p.suffix == ".pdf"), None)
        resume_p = next((p for t, p in temp_pdfs if "resume" in t and p.suffix == ".pdf"), None)
        _merge_pdfs(cover_p, resume_p, final_path)
        print(f"  Output: {final_name} (커버레터+이력서 병합)")
    elif len(pdf_parts) == 1:
        shutil.move(str(pdf_parts[0]), str(final_path))
        print(f"  Output: {final_name}")
    else:
        docx_parts = [p for _, p in temp_pdfs if p.suffix == ".docx"]
        if docx_parts:
            final_path = DEFAULT_OUTPUT / _build_output_filename(number, candidate, ".docx")
            shutil.move(str(docx_parts[0]), str(final_path))
            print(f"  Output: {final_path.name} (DOCX — PDF 변환 실패)")

    for _, tmp in temp_pdfs:
        if tmp.exists():
            tmp.unlink()

    # 사진 정리
    if downloaded_photo and downloaded_photo.exists():
        backup_original(downloaded_photo)
        downloaded_photo.unlink()

    print(f"  [OK] {final_path.name}")


def cmd_setup(_args=None):
    """setup 명령: 폴더 구조 생성 + 상태 확인"""
    dirs = [INCOMING_DIR, DEFAULT_OUTPUT, BACKUP_DIR, LOG_DIR]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    print(f"\n  BRIDGE Document Processor v2.6 — 폴더 구조")
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


def cmd_init_db(_args=None):
    """init-db 명령: file_uploads 테이블 생성"""
    _ensure_file_uploads_table()
    db = _get_db()
    count = db.execute("SELECT COUNT(*) FROM file_uploads").fetchone()[0]
    print(f"\n  [init-db] file_uploads 테이블 준비 완료")
    print(f"  DB: {DB_PATH}")
    print(f"  기존 레코드: {count}건\n")


def main():
    parser = argparse.ArgumentParser(
        description="BRIDGE Document Processor v2.6 — PII 삭제 + 강사번호"
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
    sub.add_parser("init-db", help="file_uploads 테이블 생성 (IF NOT EXISTS)")

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
    elif args.command == "init-db":
        cmd_init_db(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
