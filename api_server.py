"""
BRIDGE API Server  v2.1
===================================
bridgejob.co.kr 웹사이트용 백엔드 API

엔드포인트:
  GET  /              → 상태 확인
  GET  /api/jobs      → 공개 구인 목록 (anon)
  GET  /api/jobs/{id} → 포지션 상세
  POST /api/apply     → 구직자 지원 접수 (anon)
  POST /api/inquiry   → 구인처 문의 접수 (anon)

실행:
  uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload

환경변수 (.env):
  SUPABASE_URL=https://xxxx.supabase.co
  SUPABASE_ANON_KEY=eyJ...
  SUPABASE_SERVICE_KEY=eyJ...  (서버사이드 전용 — 노출 금지)
"""
import io
import os
import re
import sys
import json
import time
import uuid
import sqlite3
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Any
import hashlib
import asyncio
import threading

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── dotenv ──────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

# ── FastAPI / Supabase 임포트 ────────────────────────────────────────────────
try:
    from fastapi import FastAPI, HTTPException, Request, Query, status, UploadFile, File as FastFile
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from starlette.middleware.base import BaseHTTPMiddleware
    from fastapi.responses import JSONResponse, Response
    from pydantic import BaseModel, EmailStr, Field
except ImportError:
    print("[ERROR] fastapi 없음: pip install fastapi uvicorn email-validator")
    sys.exit(1)

try:
    from PIL import Image as PILImage
    _PILLOW_OK = True
except ImportError:
    _PILLOW_OK = False
    print("[INFO] Pillow 미설치 — 썸네일 생성 비활성화 (pip install Pillow)")

try:
    from supabase import create_client, Client
except ImportError:
    print("[ERROR] supabase 없음: pip install supabase")
    sys.exit(1)

# ── email_templates (확인 이메일 발송) ────────────────────────────────────────
try:
    from email_templates import send_applicant_confirmation, send_employer_confirmation
    _EMAIL_OK = True
except ImportError:
    _EMAIL_OK = False
    print("[INFO] email_templates 미설치 — 확인 이메일 발송 비활성화")

# ── security_vault (PII 필드 암호화) ─────────────────────────────────────────
try:
    from security_vault import encrypt_field, decrypt_field, is_encrypted
    _VAULT_OK = True
except Exception as _vault_exc:
    # 암호화 모듈 없이 PII 저장은 절대 허용 안 함 — 즉시 종료
    print(f"[CRITICAL] security_vault 로드 실패: {_vault_exc}")
    print("[CRITICAL] pip install cryptography 후 재시작하세요.")
    sys.exit(1)


# ── JWT Magic Link ────────────────────────────────────────────────────────────
import jwt as _jwt   # PyJWT

_JWT_SECRET  = os.getenv("JWT_SECRET") or os.getenv("BRIDGE_FIELD_KEY")
if not _JWT_SECRET:
    import secrets as _sec
    _JWT_SECRET = _sec.token_urlsafe(32)
    print("[WARN] JWT_SECRET 미설정 — 임시 랜덤 키 사용 (서버 재시작 시 기존 토큰 무효화됨)")
    print("[WARN] .env에 JWT_SECRET 를 별도로 설정하세요.")
_JWT_ALG     = "HS256"
_JWT_TTL     = timedelta(days=30)


def _make_candidate_token(candidate_id: str) -> str:
    """지원자 ID를 담은 30일짜리 JWT 생성."""
    exp = datetime.now(timezone.utc) + _JWT_TTL
    payload = {"sub": str(candidate_id), "exp": exp, "iss": "bridge-apply"}
    return _jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALG)


def _verify_candidate_token(token: str) -> Optional[str]:
    """JWT 검증 → candidate_id 반환. 만료/위조 시 None."""
    try:
        data = _jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALG],
                           options={"require": ["sub", "exp", "iss"]})
        return data.get("sub")
    except Exception:
        return None


def _dedup_key(name: str, dob: Optional[str], nationality: Optional[str]) -> str:
    """복합 중복방지 키: lower(name_no_space) + birth_year + nationality."""
    n   = re.sub(r"\s+", "", (name or "").lower())
    yr  = (dob or "")[:4] or "xxxx"
    nat = (nationality or "").lower()
    return f"{n}_{yr}_{nat}"


def _encrypt_if_needed(value: str) -> str:
    """값이 있고 아직 암호화되지 않은 경우에만 암호화."""
    if not value or not isinstance(value, str):
        return value
    return value if is_encrypted(value) else encrypt_field(value)

# ── PII 마스킹 설정 ───────────────────────────────────────────────────────────
# DB 컬럼 단위 차단 (응답 JSON에서 키 자체를 제거)
_PII_BLOCKED_KEYS: frozenset[str] = frozenset({
    # 학교/기관명
    "school_name", "school_name_en", "school_name_kr",
    # 이름 (후보자 및 담당자)
    "full_name", "first_name", "last_name", "name",
    "contact_name", "contact_person",
    "recruiter_name", "recruiter_email",
    # 직책/포지션 (담당자 직책 — 채용 포지션 타입과 혼동 주의)
    "contact_position", "contact_title",
    "recruiter_position", "recruiter_title",
    "position_title", "staff_position",
    # 연락처
    "phone", "phone_primary", "phone_kakao", "mobile",
    "email",
    # 주소
    "location_full", "address", "district",
    # 사업자/신원
    "business_registration",
    "passport", "passport_number", "passport_status",
    "criminal_record", "criminal_record_check",
    "health_info",
    "employer_id", "internal_notes",
})

# 값 수준 정규식 마스킹 — 블록키를 통과한 문자열에 잔류 PII가 있을 경우 대비
_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    # 한국 휴대전화 (010-xxxx-xxxx / 01x-xxx-xxxx)
    (re.compile(r"\b01[016789][- ]?\d{3,4}[- ]?\d{4}\b"), "***-****-****"),
    # 국제 전화 (+1 555 000 0000 등)
    (re.compile(r"\+\d{1,3}[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}"), "+*-***-***-****"),
    # 이메일
    (re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"), "***@***.***"),
    # 사업자등록번호 (xxx-xx-xxxxx)
    (re.compile(r"\b\d{3}-\d{2}-\d{5}\b"), "***-**-*****"),
    # 주민등록번호 앞자리+뒷자리 패턴
    (re.compile(r"\b\d{6}-[1-4]\d{6}\b"), "******-*******"),
    # 한국어 이름 — 담당자/성명 컨텍스트 뒤에 오는 2-4자 한글
    (re.compile(r"(?:담당자|성명|이름|문의|연락처)[:：\s]{0,3}([가-힣]{2,4})"), "[REDACTED-NAME]"),
    # 영어 이름 — "Name:", "Contact:", "Teacher:" 뒤 Title Case
    (re.compile(r"(?:Name|Contact|Teacher|Recruiter|Manager):\s*([A-Z][a-z]+ [A-Z][a-z]+)"), "[REDACTED-NAME]"),
]


def _scrub_value(v: str) -> str:
    """Apply all PII regex patterns to a single string value."""
    for pattern, replacement in _PII_PATTERNS:
        v = pattern.sub(replacement, v)
    return v


def _scrub_obj(obj: Any) -> Any:
    """Recursively walk a JSON-deserialized object and mask PII."""
    if isinstance(obj, dict):
        return {
            k: _scrub_obj(v)
            for k, v in obj.items()
            if k not in _PII_BLOCKED_KEYS   # drop blocked keys entirely
        }
    if isinstance(obj, list):
        return [_scrub_obj(item) for item in obj]
    if isinstance(obj, str):
        return _scrub_value(obj)
    return obj


class PIIMaskingMiddleware(BaseHTTPMiddleware):
    """
    Response middleware: intercepts all JSON responses and strips / masks PII.
    Adds X-PII-Scrubbed: true header for audit tracing.
    Zero-overhead for non-JSON responses (static files, health checks).
    """
    _SEC_HEADERS = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-XSS-Protection": "1; mode=block",
    }

    def _add_sec_headers(self, response):
        for k, v in self._SEC_HEADERS.items():
            response.headers[k] = v

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        ct = response.headers.get("content-type", "")
        if "application/json" not in ct:
            self._add_sec_headers(response)
            return response

        # 관리자 인증된 /api/admin/ 요청은 PII 마스킹 통과 (원본 데이터 반환)
        _ak = os.getenv("ADMIN_API_KEY", "")
        if (request.url.path.startswith("/api/admin/")
                and _ak
                and request.headers.get("x-admin-key", "") == _ak):
            self._add_sec_headers(response)
            return response

        # Accumulate response body
        body_parts: list[bytes] = []
        async for chunk in response.body_iterator:
            body_parts.append(chunk)
        raw_body = b"".join(body_parts)

        try:
            data = json.loads(raw_body)
            clean = _scrub_obj(data)
            clean_body = json.dumps(clean, ensure_ascii=False).encode("utf-8")
        except (json.JSONDecodeError, Exception):
            clean_body = raw_body   # pass through if not parseable JSON

        headers = dict(response.headers)
        headers["content-length"] = str(len(clean_body))
        headers["x-pii-scrubbed"] = "true"
        for k, v in self._SEC_HEADERS.items():
            headers[k] = v

        return Response(
            content=clean_body,
            status_code=response.status_code,
            headers=headers,
            media_type="application/json",
        )


# ── 설정 ─────────────────────────────────────────────────────────────────────
SUPABASE_URL      = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")   # 공개 API용
SUPABASE_SVC_KEY  = os.getenv("SUPABASE_SERVICE_KEY", "") # 서버사이드 삽입용

# CORS 허용 출처 — 기본 도메인 + 환경변수 추가분 병합
_CORE_ORIGINS = [
    "https://bridgejob.co.kr",
    "https://www.bridgejob.co.kr",
    "https://bridge-chi-lime.vercel.app",
    "https://bridge-n7hk.onrender.com",
]
_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:8080",
]
_cors_env = os.getenv("CORS_ORIGINS", "")
_extra = [o.strip() for o in _cors_env.split(",") if o.strip()] if _cors_env else []
ALLOWED_ORIGINS = list(dict.fromkeys(_CORE_ORIGINS + _extra + _DEV_ORIGINS))

# ── 앱 초기화 ─────────────────────────────────────────────────────────────────
# 프로덕션에서는 API 문서 비활성화 (BRIDGE_ENV=production 설정 시)
_IS_PROD = os.getenv("BRIDGE_ENV", os.getenv("ENV", "")).lower() in ("production", "prod")

app = FastAPI(
    title="BRIDGE Recruitment API",
    description="bridgejob.co.kr 웹사이트 백엔드",
    version="1.0.0",
    docs_url=None if _IS_PROD else "/docs",
    redoc_url=None if _IS_PROD else "/redoc",
)

# 보안 미들웨어 — 헤더 + Rate Limit + 감사 로그
try:
    from security_middleware import SecurityMiddleware
    app.add_middleware(SecurityMiddleware)
except ImportError:
    pass  # 선택적: 파일 없으면 무시

# PII 마스킹 미들웨어 — CORS보다 먼저 등록해야 응답 전체를 커버
app.add_middleware(PIIMaskingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Admin-Key", "X-Bridge-Signature"],
)

# ── Supabase 클라이언트 (지연 초기화) ─────────────────────────────────────────
_anon_client: Optional["Client"] = None
_svc_client:  Optional["Client"] = None


def get_anon_client() -> "Client":
    global _anon_client
    if _anon_client is None:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise RuntimeError(".env 에 SUPABASE_URL / SUPABASE_ANON_KEY 필요")
        _anon_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _anon_client


def get_svc_client() -> "Client":
    global _svc_client
    if _svc_client is None:
        if not SUPABASE_URL or not SUPABASE_SVC_KEY:
            raise RuntimeError(".env 에 SUPABASE_URL / SUPABASE_SERVICE_KEY 필요")
        _svc_client = create_client(SUPABASE_URL, SUPABASE_SVC_KEY)
    return _svc_client


# ── 요청 모델 ─────────────────────────────────────────────────────────────────
class CandidateApply(BaseModel):
    """
    구직자 지원 웹폼 — 구글폼 42개 항목 100% 매핑
    Google Form + Native Web Form 병렬 운영 공통 스키마
    """
    # ── 기본 식별 ──────────────────────────────────────────────────────────
    full_name:               str  = Field(..., min_length=2, max_length=100)  # [ENCRYPT]
    email:                   Optional[str] = None   # [ENCRYPT]
    how_to:                  Optional[str] = None   # How to (소스 경로)
    file_urls:               Optional[str] = None   # Attach your files (링크)

    # ── 인적사항 ───────────────────────────────────────────────────────────
    nationality:             Optional[str] = None
    ancestry:                Optional[str] = None   # Family Ancestry Background
    dob:                     Optional[str] = None   # Date of Birth
    gender:                  Optional[str] = None
    current_location:        Optional[str] = None
    marital_status:          Optional[str] = None   # Marital Status
    dependents:              Optional[str] = None   # Dependents
    pets:                    Optional[str] = None   # Pets

    # ── 학력 & 자격 ────────────────────────────────────────────────────────
    education:               Optional[str] = None   # Educational Background
    major:                   Optional[str] = None   # Major
    certification:           Optional[str] = None   # Certification

    # ── 비자 & 서류 ────────────────────────────────────────────────────────
    e_visa:                  Optional[str] = None   # E visa
    arc_holders:             Optional[str] = None   # ARC holders
    passport:                Optional[str] = None   # Passport [ENCRYPT]
    criminal_record:         Optional[str] = None   # Criminal Record [ENCRYPT]
    doc_status:              Optional[str] = None   # Document Status

    # ── 근무 선호 ──────────────────────────────────────────────────────────
    start_date:              Optional[str] = None   # Start date
    area_prefs:              Optional[str] = None   # TargetArea prefs
    target_age:              Optional[str] = None   # (수업 연령대 선호)
    job_prefs:               Optional[str] = None   # Job prefs (Notes)
    experience:              Optional[str] = None   # Experience
    employment:              Optional[str] = None   # Employment (현 고용주 인지 여부)
    reference:               Optional[str] = None   # Employment Reference
    interview_time:          Optional[str] = None   # Interview time

    # ── 급여 & 주거 ────────────────────────────────────────────────────────
    current_salary:          Optional[str] = None   # Current salary
    desired_salary:          Optional[str] = None   # Desired salary
    housing:                 Optional[str] = None   # Housing
    personal_considerations: Optional[str] = None   # Personal Considerations

    # ── 고위험 PII (최강 암호화) ───────────────────────────────────────────
    religion:                Optional[str] = None   # Religion [ENCRYPT]
    health_info:             Optional[str] = None   # Health Information [ENCRYPT]
    criminal_record_check:   Optional[str] = None   # Criminal Record Check [ENCRYPT]

    # ── 연락처 ─────────────────────────────────────────────────────────────
    kakaotalk:               Optional[str] = None   # KakaoTalk [ENCRYPT]
    mobile_phone:            Optional[str] = None   # Mobile Phone [ENCRYPT]

    # ── 동의 ───────────────────────────────────────────────────────────────
    agreement:               Optional[str] = None   # Agreement
    facts:                   Optional[str] = None   # Facts

    # ── 관리자 메모 ────────────────────────────────────────────────────────
    admin_notes:             Optional[str] = None   # 메모 (Google Form 기입란)

    # ── 2차 폼 / 병렬 운영 ────────────────────────────────────────────────
    apply_token:             Optional[str] = None   # JWT magic link
    source:                  Optional[str] = None   # 'web_form' | 'google_form'


class ClientInquiry(BaseModel):
    """
    구인처 채용 문의 — 구글폼 43개 항목 100% 매핑
    Google Form + Native Web Form 병렬 운영 공통 스키마
    """
    # ── 담당자 식별 ────────────────────────────────────────────────────────
    email:               Optional[str] = None   # 이메일 주소 [ENCRYPT]
    contact_name:        Optional[str] = None   # 성함 [ENCRYPT]
    contact_position:    Optional[str] = None   # 직책
    phone:               Optional[str] = None   # 휴대전화 [ENCRYPT]
    business_registration: Optional[str] = None # 사업자 [ENCRYPT]

    # ── 학교 / 기관 정보 ───────────────────────────────────────────────────
    school_name:         str = Field(..., min_length=2, max_length=200)  # 학교이름 (필수)
    school_name_en:      Optional[str] = None   # Name (English)
    hiring_history:      Optional[str] = None   # 채용이력
    school_location:     Optional[str] = None   # 근무처소재지
    vacancies:           Optional[str] = None   # 채용인원
    native_count:        Optional[str] = None   # 원어민강사 현재 수

    # ── 근무 조건 ──────────────────────────────────────────────────────────
    start_date:          Optional[str] = None   # 희망시작일
    teaching_age:        Optional[str] = None   # 수업대상
    working_days:        Optional[str] = None   # 근무요일
    schedule:            Optional[str] = None   # 근무일정 (시간)
    working_hours:       Optional[str] = None   # 총 근무시간
    class_size:          Optional[str] = None   # 학생수
    avg_lessons:         Optional[str] = None   # 평균강의
    prep_time:           Optional[str] = None   # 프렙타임

    # ── 선호 대상 ──────────────────────────────────────────────────────────
    preferred_candidate: Optional[str] = None   # 선호대상

    # ── 급여 조건 ──────────────────────────────────────────────────────────
    salary_raw:          Optional[str] = None   # 급여조건

    # ── 숙소 & 주거 ────────────────────────────────────────────────────────
    housing_type:        Optional[str] = None   # 거주지 (숙소 형태)
    housing_provided:    Optional[str] = None   # 숙소제공
    housing_detail:      Optional[str] = None   # 숙소관련

    # ── 복지 & 휴가 ────────────────────────────────────────────────────────
    travel_support:      Optional[str] = None   # 이동지원
    benefits:            Optional[str] = None   # 복지
    vacation:            Optional[str] = None   # (기존 호환)
    paid_vacation:       Optional[str] = None   # 유급휴일
    vacation_includes:   Optional[str] = None   # 휴일 포함여부

    # ── 근로계약 ───────────────────────────────────────────────────────────
    contract_type:       Optional[str] = None   # 계약구분
    break_time:          Optional[str] = None   # 휴게시간
    job_responsibilities: Optional[str] = None  # 업무책임
    sick_leave:          Optional[str] = None   # 보건휴가
    meal:                Optional[str] = None   # (기존 호환)
    meal_provided:       Optional[str] = None   # 식사
    meal_allowance:      Optional[str] = None   # 식대

    # ── 메모 (이중 언어) ────────────────────────────────────────────────────
    memo:                Optional[str] = None   # (기존 호환)
    memo_kr:             Optional[str] = None   # 메모
    memo_en:             Optional[str] = None   # Memo

    # ── 동의 & 기타 ────────────────────────────────────────────────────────
    privacy_policy:      Optional[str] = None   # 개인정보처리방침 동의

    # ── 관리 ───────────────────────────────────────────────────────────────
    location:            Optional[str] = None   # (기존 호환)
    source:              Optional[str] = None   # 'web_form' | 'google_form'


# ── 공통 응답 ─────────────────────────────────────────────────────────────────
def ok(data=None, message: str = "ok"):
    return {"success": True, "message": message, "data": data}


def err(message: str, code: int = 400):
    raise HTTPException(status_code=code, detail=message)


# ── 라우트 ────────────────────────────────────────────────────────────────────
@app.get("/", tags=["health"])
async def root():
    """서버 상태 확인"""
    return {
        "service": "BRIDGE Recruitment API",
        "status":  "running",
        "time":    datetime.now(timezone.utc).isoformat(),
        "docs":    "/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Render / 외부 모니터링용 헬스체크"""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# ── Render 슬립 방지 — 10분마다 self-ping ──────────────────────────────────────
_RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "")

def _keep_alive_loop():
    """백그라운드 스레드: 10분마다 /health self-ping"""
    import urllib.request
    url = f"{_RENDER_URL}/health" if _RENDER_URL else ""
    if not url:
        return
    while True:
        time.sleep(600)  # 10분
        try:
            urllib.request.urlopen(url, timeout=10)
        except Exception:
            pass

if _RENDER_URL:
    _t = threading.Thread(target=_keep_alive_loop, daemon=True)
    _t.start()


def _job_row_to_public(row: dict) -> dict:
    """SQLite jobs row → PublicJob 형태로 매핑 (민감 필드 제외)"""
    teaching_age_raw = row.get("teaching_age") or ""
    # "Kindy - Elem" 같은 텍스트를 age group 배열로 변환
    age_map = {
        "kindy": "kindergarten", "kindergarten": "kindergarten",
        "elem": "elementary", "elementary": "elementary",
        "pre_k": "pre_k", "pre-k": "pre_k", "prek": "pre_k",
        "middle": "middle", "high": "high", "adult": "adult",
    }
    age_groups = []
    for token in re.split(r"[,/\-&·\s]+", teaching_age_raw.lower()):
        token = token.strip()
        if token in age_map and age_map[token] not in age_groups:
            age_groups.append(age_map[token])

    benefits_raw = row.get("benefits") or ""
    benefits_list = [b.strip() for b in benefits_raw.split(",") if b.strip()] if benefits_raw else []

    return {
        "location":                row.get("city") or row.get("location"),
        "job_id":                  row.get("job_code", ""),
        "starting_date":           row.get("start_date"),
        "teaching_age":            age_groups or None,
        "class_size":              row.get("class_size"),
        "working_hours":           row.get("working_hours"),
        "monthly_salary":          row.get("salary_raw"),
        "teaching_hours_per_week": row.get("teach_hrs_week"),
        "vacation":                row.get("vacation"),
        "native_teacher_count":    row.get("native_count"),
        "housing":                 row.get("housing"),
        "preferences":             None,
        "employee_benefits":       benefits_list or None,
        "is_hot":                  bool(row.get("is_hot", 0)),
        "employment_type":         "part_time" if row.get("is_part_time") else "full_time",
        "hours_per_day":           row.get("daily_hours"),
        "status":                  row.get("status", "open"),
    }


@app.get("/api/jobs", tags=["jobs"])
async def list_jobs(
    request:   Request,
    city:      Optional[str] = None,
    is_hot:    Optional[bool] = None,
    include_closed: Optional[bool] = None,
    limit:     int = 50,
    offset:    int = 0,
):
    """
    공개 구인 목록 조회 (SQLite, status='open' 만 반환)
    - city: 도시 필터 (서울, 인천, 수원 등)
    - is_hot: HOT 포지션만 (true/false)
    - include_closed: true면 closed 포함 (admin용)
    - limit / offset: 페이지네이션
    """
    if not _rate_ok(_ip_hash(request), window=60, max_posts=60):
        raise HTTPException(429, "Too many requests. Please slow down.")
    try:
        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        try:
            where = ["is_deleted = 0"]
            params: list[Any] = []

            # include_closed requires admin key
            if include_closed and _ADMIN_KEY and request.headers.get("x-admin-key", "") == _ADMIN_KEY:
                pass  # no status filter
            else:
                where.append("status = ?")
                params.append("open")

            if city:
                city = city.strip()[:50]
                where.append("(city LIKE ? OR location LIKE ?)")
                params.extend([f"%{city}%", f"%{city}%"])
            if is_hot is not None:
                where.append("is_hot = ?")
                params.append(1 if is_hot else 0)

            sql = (
                "SELECT * FROM jobs WHERE " + " AND ".join(where)
                + " ORDER BY is_hot DESC, created_at DESC"
                + " LIMIT ? OFFSET ?"
            )
            params.extend([limit, offset])

            rows = conn.execute(sql, params).fetchall()
            data = [_job_row_to_public(dict(r)) for r in rows]
            return ok(data=data, message=f"{len(data)}건 조회")
        finally:
            conn.close()

    except Exception as e:
        logging.getLogger("bridge.api").error("list_jobs 실패: %s", e, exc_info=True)
        err("구인 목록을 불러올 수 없습니다. 잠시 후 다시 시도해주세요.", 500)


@app.get("/api/jobs/{job_id}", tags=["jobs"])
async def get_job(job_id: str, request: Request):
    """포지션 상세 조회 — 민감 필드(구인처 연락처/주소 등) 제외, SQLite"""
    if not _rate_ok(_ip_hash(request), window=60, max_posts=60):
        raise HTTPException(429, "Too many requests. Please slow down.")
    try:
        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM jobs WHERE id = ? AND status = ? AND is_deleted = 0",
                [job_id, "open"],
            ).fetchone()
            if not row:
                err("포지션을 찾을 수 없습니다.", 404)
            return ok(data=_job_row_to_public(dict(row)))
        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        logging.getLogger("bridge.api").error("get_job 실패: %s", e, exc_info=True)
        err("포지션 정보를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.", 500)


# 구직자 암호화 필드 — 고위험 PII 전체 포함
_CANDIDATE_ENCRYPT = {
    "full_name",            # 식별 가능 이름
    "email",                # 이메일
    "mobile_phone",         # 휴대폰
    "kakaotalk",            # 카카오톡
    "passport",             # 여권 (번호/상태)
    "criminal_record",      # 전과기록 (자체 기술)
    "religion",             # 종교 [고위험]
    "health_info",          # 건강 정보 [고위험]
    "criminal_record_check", # 범죄경력조회 [고위험]
}


@app.post("/api/apply", status_code=status.HTTP_201_CREATED, tags=["candidates"])
async def apply(request: Request, body: CandidateApply):
    if not _rate_ok(_ip_hash(request), window=3600, max_posts=10):
        raise HTTPException(429, "Too many requests. Please try again later.")
    """
    구직자 지원 접수 (1차 / 2차 통합)

    1차 제출: INSERT → JWT magic link 토큰 반환
    2차 제출: apply_token 검증 → UPDATE (누적)
    토큰 없음: dedup_key 복합키로 기존 레코드 탐색 → UPSERT
    """
    try:
        now_iso = datetime.now(timezone.utc).isoformat()

        payload = body.model_dump(exclude_none=True)
        token_in = payload.pop("apply_token", None)

        # PII 암호화
        for field in _CANDIDATE_ENCRYPT:
            if field in payload and payload[field]:
                payload[field] = _encrypt_if_needed(str(payload[field]))

        payload["updated_at"] = now_iso

        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.row_factory = sqlite3.Row
        try:
            existing_id: Optional[str] = None

            # ── 경로 A: JWT 토큰으로 기존 레코드 찾기
            if token_in:
                cid = _verify_candidate_token(token_in)
                if cid:
                    existing_id = cid

            # ── 경로 B: email로 기존 레코드 탐색
            if not existing_id and body.email:
                row = conn.execute(
                    "SELECT candidate_id FROM candidates WHERE email = ? LIMIT 1",
                    (payload.get("email", body.email),),
                ).fetchone()
                if row:
                    existing_id = row["candidate_id"]

            # ── UPDATE (2차 누적)
            if existing_id:
                sets = ", ".join(f"{k} = ?" for k in payload if k != "candidate_id")
                vals = [v for k, v in payload.items() if k != "candidate_id"]
                vals.append(existing_id)
                conn.execute(f"UPDATE candidates SET {sets} WHERE candidate_id = ?", vals)
                conn.commit()
                tok = _make_candidate_token(existing_id)
                return ok(
                    data={"id": existing_id, "apply_token": tok, "mode": "updated"},
                    message="지원 정보가 업데이트되었습니다."
                )

            # ── INSERT (1차 신규)
            import uuid
            new_id = f"cnd_{uuid.uuid4().hex[:12]}"
            payload["candidate_id"] = new_id
            payload["source"]     = payload.get("source") or "web_form"
            payload["status"]     = "Active"
            payload["created_at"] = now_iso

            cols = ", ".join(payload.keys())
            placeholders = ", ".join("?" * len(payload))
            conn.execute(
                f"INSERT INTO candidates ({cols}) VALUES ({placeholders})",
                list(payload.values()),
            )
            conn.commit()

            token_out = _make_candidate_token(new_id)

            # 확인 이메일 발송 (실패해도 접수는 완료)
            if _EMAIL_OK and body.email:
                send_applicant_confirmation(body.email, body.full_name)

            return ok(
                data={"id": new_id, "apply_token": token_out, "mode": "created"},
                message="지원이 접수되었습니다. 담당자가 검토 후 연락드리겠습니다."
            )
        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        import logging as _log_apply
        _log_apply.getLogger("bridge.api").error("apply 접수 실패: %s", e, exc_info=True)
        err("접수에 실패했습니다. 잠시 후 다시 시도해주세요.", 500)


@app.post("/api/inquiry", status_code=status.HTTP_201_CREATED, tags=["clients"])
async def inquiry(request: Request, body: ClientInquiry):
    if not _rate_ok(_ip_hash(request), window=3600, max_posts=5):
        raise HTTPException(429, "Too many requests. Please try again later.")
    """
    구인처 문의 접수
    - 학교/학원 → 채용 문의 → client_inquiries 테이블 INSERT
    - 연락처/담당자명은 security_vault AES-256-GCM 암호화 후 저장
    """
    # 구인처 암호화: 식별 가능 정보 + 사업자
    _INQUIRY_ENCRYPT = {"phone", "email", "contact_name", "business_registration"}

    try:
        payload = body.model_dump(exclude_none=True)
        # 연락처 PII 암호화 (storage 전 마지막 레이어)
        for field in _INQUIRY_ENCRYPT:
            if field in payload and payload[field]:
                payload[field] = _encrypt_if_needed(str(payload[field]))

        payload["source"]       = "web_form"
        payload["inbox_status"] = "new"
        payload["submitted_at"] = datetime.now(timezone.utc).isoformat()

        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            cols = ", ".join(payload.keys())
            placeholders = ", ".join("?" * len(payload))
            cur = conn.execute(
                f"INSERT INTO client_inquiries ({cols}) VALUES ({placeholders})",
                list(payload.values()),
            )
            conn.commit()
            new_id = cur.lastrowid

            # 확인 이메일 발송 (실패해도 접수는 완료)
            if _EMAIL_OK and body.email:
                send_employer_confirmation(body.email, body.school_name, body.contact_name or "")

            return ok(
                data={"id": new_id},
                message="문의가 접수되었습니다. 빠른 시일 내에 연락드리겠습니다."
            )
        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        import logging as _log_inq
        _log_inq.getLogger("bridge.api").error("inquiry 접수 실패: %s", e, exc_info=True)
        err("문의 접수에 실패했습니다. 잠시 후 다시 시도해주세요.", 500)


# ── 전역 예외 처리 ─────────────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging as _logging
    _logging.getLogger("bridge.api").error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."},
    )


# ── Admin: ad_posts 대시보드 ──────────────────────────────────────────────────
_ADMIN_DB_PATH = Path(os.getenv("DB_PATH", os.getenv("BRIDGE_DB_PATH", str(Path(__file__).resolve().parent / "master.db"))))
_ADMIN_KEY     = os.getenv("ADMIN_API_KEY", "")
_ADMIN_PW      = os.getenv("ADMIN_PASSWORD", "")

if not _ADMIN_KEY:
    import logging as _log_adm
    _log_adm.getLogger("bridge.api").warning(
        "[SECURITY] ADMIN_API_KEY 미설정 — 관리자 엔드포인트가 인증 없이 노출됩니다! "
        ".env에 ADMIN_API_KEY를 반드시 설정하세요."
    )


def _check_admin(request: Request):
    """ADMIN_API_KEY 헤더 검증. 프로덕션에서 키 미설정 시 접근 차단."""
    if not _ADMIN_KEY:
        if _IS_PROD:
            raise HTTPException(status_code=503, detail="관리자 기능이 비활성화되어 있습니다.")
        # 개발 환경에서만 키 없이 통과 허용
        return
    if request.headers.get("x-admin-key", "") != _ADMIN_KEY:
        raise HTTPException(status_code=403, detail="관리자 키가 올바르지 않습니다.")


@app.post("/api/admin/login", tags=["admin"])
async def admin_login(request: Request):
    """비밀번호 검증 → ADMIN_API_KEY 반환."""
    ip = _ip_hash(request)
    if not _rate_ok(ip, window=300, max_posts=10):
        raise HTTPException(429, "Too many login attempts.")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")
    pw = str(body.get("password", ""))
    if not _ADMIN_PW or not _ADMIN_KEY:
        raise HTTPException(503, "관리자 인증이 설정되지 않았습니다.")
    if pw != _ADMIN_PW:
        raise HTTPException(403, "비밀번호가 올바르지 않습니다.")
    return ok(data={"api_key": _ADMIN_KEY}, message="로그인 성공")


@app.post("/api/admin/reset-blacklist", tags=["admin"])
async def admin_reset_blacklist(request: Request):
    """IP 블랙리스트 초기화 (관리자 전용)."""
    _check_admin(request)
    bl_path = Path(os.getenv("AUDIT_DIR", str(Path(__file__).resolve().parent / "audit"))) / "ip_blacklist.json"
    bl_path.write_text("{}", encoding="utf-8")
    # 메모리 블랙리스트도 초기화
    try:
        from security_middleware import ip_blacklist
        ip_blacklist._list.clear()
        ip_blacklist._save()
    except Exception:
        pass
    return ok(message="IP 블랙리스트 초기화 완료")


@app.get("/api/admin/dashboard", tags=["admin"])
async def admin_dashboard(request: Request):
    """관리자 대시보드 — 전체 통계 + 최근 활동."""
    _check_admin(request)

    stats: dict = {}
    recent_activity: list[dict] = []

    # ── SQLite 통계 (community_posts, interviews, ad_posts) ────────────────
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        # 게시글 수
        r = conn.execute(
            "SELECT COUNT(*) AS n FROM community_posts WHERE is_deleted=0"
        ).fetchone()
        stats["posts"] = r["n"] if r else 0

        # 예정 인터뷰
        try:
            r = conn.execute(
                "SELECT COUNT(*) AS n FROM interviews WHERE is_deleted=0 AND status='scheduled'"
            ).fetchone()
            stats["interviews_scheduled"] = r["n"] if r else 0
        except Exception:
            stats["interviews_scheduled"] = 0

        # Ad posts 통계
        try:
            r = conn.execute(
                "SELECT COUNT(*) AS n FROM ad_posts"
            ).fetchone()
            stats["ad_posts"] = r["n"] if r else 0
        except Exception:
            stats["ad_posts"] = 0

        # 최근 활동 피드: 게시글 최신 5건
        recent_posts = conn.execute(
            """SELECT id, board, title, created_at, 'post' AS type
               FROM community_posts WHERE is_deleted=0
               ORDER BY created_at DESC LIMIT 5"""
        ).fetchall()
        for rp in recent_posts:
            recent_activity.append(dict(rp))

        # 최근 활동 피드: 인터뷰 최신 5건
        try:
            recent_ivs = conn.execute(
                """SELECT id, candidate_name, interview_date, interview_time,
                          status, created_at, 'interview' AS type
                   FROM interviews WHERE is_deleted=0
                   ORDER BY created_at DESC LIMIT 5"""
            ).fetchall()
            for ri in recent_ivs:
                recent_activity.append(dict(ri))
        except Exception:
            pass

    finally:
        conn.close()

    # ── SQLite 통계 (candidates, jobs, client_inquiries) ────────────────────
    conn2 = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn2.execute("PRAGMA busy_timeout = 5000")
    conn2.row_factory = sqlite3.Row
    try:
        # 지원자 수
        r = conn2.execute("SELECT COUNT(*) AS n FROM candidates").fetchone()
        stats["candidates"] = r["n"] if r else 0

        # Active 지원자
        r = conn2.execute(
            "SELECT COUNT(*) AS n FROM candidates WHERE status='Active'"
        ).fetchone()
        stats["candidates_active"] = r["n"] if r else 0

        # Jobs 수
        try:
            r = conn2.execute(
                "SELECT COUNT(*) AS n FROM jobs WHERE status='open'"
            ).fetchone()
            stats["jobs_open"] = r["n"] if r else 0
        except Exception:
            stats["jobs_open"] = 0

        # 채용의뢰 수
        try:
            r = conn2.execute(
                "SELECT COUNT(*) AS n FROM client_inquiries"
            ).fetchone()
            stats["inquiries"] = r["n"] if r else 0
        except Exception:
            stats["inquiries"] = 0

        stats["payments_total"] = 0
        stats["payments_confirmed"] = 0
        stats["revenue"] = 0
    finally:
        conn2.close()

    # 최근 활동을 시간순 정렬
    recent_activity.sort(
        key=lambda x: x.get("created_at", ""), reverse=True
    )

    return ok(data={"stats": stats, "recent_activity": recent_activity[:10]})


def _read_ad_posts(
    status_filter:   Optional[str],
    platform_filter: Optional[str],
    limit:           int,
) -> tuple[list[dict], dict]:
    """master.db 에서 ad_posts 읽기. (rows, stats) 반환."""
    if not _ADMIN_DB_PATH.exists():
        return [], {"error": f"master.db not found at {_ADMIN_DB_PATH}"}

    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.row_factory = sqlite3.Row

    # 전체 통계
    stat_rows = conn.execute(
        "SELECT status, COUNT(*) AS n FROM ad_posts GROUP BY status"
    ).fetchall()
    stats = {r["status"]: r["n"] for r in stat_rows}
    stats["total"] = sum(stats.values())

    # 플랫폼 목록
    platforms = [
        r[0] for r in conn.execute(
            "SELECT DISTINCT platform FROM ad_posts ORDER BY platform"
        ).fetchall()
    ]
    stats["platforms"] = platforms

    # 데이터 조회
    where_parts: list[str] = []
    params: list = []
    if status_filter:
        where_parts.append("status = ?")
        params.append(status_filter)
    if platform_filter:
        where_parts.append("platform = ?")
        params.append(platform_filter)

    where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    params.append(limit)

    rows = conn.execute(
        f"""
        SELECT id, job_code, seq, platform, status,
               ad_title, ad_body,
               draft_at, posted_at, posted_url,
               screenshot_path, error_msg
        FROM   ad_posts
        {where}
        ORDER BY id DESC
        LIMIT  ?
        """,
        params,
    ).fetchall()

    conn.close()
    return [dict(r) for r in rows], stats


@app.get("/api/admin/ad-posts", tags=["admin"])
async def admin_ad_posts(
    request:  Request,
    status:   Optional[str] = None,
    platform: Optional[str] = None,
    limit:    int = 200,
):
    """
    ad_posts 대시보드 데이터 (master.db → SQLite)
    보호: ADMIN_API_KEY 환경변수가 설정된 경우 X-Admin-Key 헤더 필수
    """
    _check_admin(request)
    rows, stats = _read_ad_posts(status, platform, limit)
    return ok(
        data={"stats": stats, "posts": rows},
        message=f"{len(rows)}건 조회",
    )


# ── Admin: Candidates Grid ────────────────────────────────────────────────────
_ADMIN_DECRYPT_FIELDS = {
    "full_name", "email",
    "mobile_phone", "kakaotalk",
    "passport", "criminal_record",
    "religion", "health_info", "criminal_record_check",
}


def _decrypt_row(row: dict) -> dict:
    """관리자용: 암호화된 PII 필드를 복호화."""
    import logging as _log_dec
    for field in _ADMIN_DECRYPT_FIELDS:
        val = row.get(field)
        if val and is_encrypted(val):
            try:
                row[field] = decrypt_field(val)
            except Exception as e:
                _log_dec.getLogger("bridge.security").error(
                    "PII 복호화 실패 — field=%s row_id=%s: %s",
                    field, row.get("id", "?"), e,
                )
                row[field] = "[복호화 실패]"
    return row


def _sanitize_str(v):
    """Remove control characters that break JSON parsing."""
    if not isinstance(v, str):
        return v
    import re as _re_san
    v = v.replace('\x00', '')
    v = _re_san.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', v)
    return v


_ACTIVE_STATUSES = {"new", "Active", "reviewing", "interviewing", "offered"}
_PAST_STATUSES = {"placed", "rejected", "withdrawn", "inactive", "Inactive", "Closed", "Deleted"}


@app.get("/api/admin/candidates", tags=["admin"])
async def admin_candidates(
    request:     Request,
    search:      Optional[str] = None,
    nationality: Optional[str] = None,
    visa:        Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit:       int = 9999,
    offset:      int = 0,
):
    """
    지원자 목록 — SQLite. status=active|past|<specific> 필터 지원.
    보호: X-Admin-Key 필수
    """
    _check_admin(request)
    try:
        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.row_factory = sqlite3.Row
        try:
            where = ["1=1"]
            params: list = []
            if search:
                where.append("(full_name LIKE ? OR email LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%"])
            if nationality:
                where.append("nationality = ?")
                params.append(nationality)
            if visa:
                where.append("e_visa LIKE ?")
                params.append(f"%{visa}%")
            if status_filter and status_filter != "all":
                if status_filter == "active":
                    placeholders = ",".join("?" * len(_ACTIVE_STATUSES))
                    where.append(f"status IN ({placeholders})")
                    params.extend(_ACTIVE_STATUSES)
                elif status_filter == "past":
                    placeholders = ",".join("?" * len(_PAST_STATUSES))
                    where.append(f"status IN ({placeholders})")
                    params.extend(_PAST_STATUSES)
                else:
                    where.append("status = ?")
                    params.append(status_filter)

            where_sql = " AND ".join(where)

            total_row = conn.execute(
                f"SELECT COUNT(*) FROM candidates WHERE {where_sql}", params
            ).fetchone()
            total = total_row[0] if total_row else 0

            rows_raw = conn.execute(
                f"""SELECT * FROM candidates
                    WHERE {where_sql}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?""",
                params + [limit, offset],
            ).fetchall()

            candidates = []
            for r in rows_raw:
                d = dict(r)
                d["id"] = d.pop("candidate_id", d.get("id"))
                d.setdefault("admin_notes", d.get("notes", ""))
                d.setdefault("photo_url", None)
                d.setdefault("thumb_url", None)
                d.setdefault("target_age", d.get("target", ""))
                for k, v in d.items():
                    d[k] = _sanitize_str(v)
                candidates.append(d)

            import json as _json_cand
            payload = ok(
                data={"total": total, "candidates": candidates},
                message=f"{len(candidates)}명 조회",
            )
            return JSONResponse(
                content=_json_cand.loads(
                    _json_cand.dumps(payload, ensure_ascii=False, default=str)
                )
            )
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        import logging as _log_cand
        _log_cand.getLogger("bridge.api").error("admin_candidates 조회 실패: %s", e, exc_info=True)
        err("지원자 목록을 불러올 수 없습니다.", 500)


@app.patch("/api/admin/candidates/{candidate_id}", tags=["admin"])
async def admin_update_candidate(
    candidate_id: str,
    request:      Request,
    body:         dict,
):
    """인라인 편집: 관리 가능 필드."""
    _check_admin(request)
    # admin_notes → notes 매핑
    if "admin_notes" in body:
        body["notes"] = body.pop("admin_notes")
    EDITABLE = {
        "notes", "reference", "status", "assigned_to",
        "contract_offered", "contract_progress",
        "email_contract", "email_immigration", "email_overseas",
        "email_transition", "email_arrival",
        "placed_company", "placed_salary", "start_month",
        "housing_detail", "referral_fee", "process_date", "past_placement",
        "recruiter_memo", "preferences", "dislikes",
        "residence_type", "start_detail", "target_level", "housing_type",
    }
    update = {k: v for k, v in body.items() if k in EDITABLE}
    if not update:
        raise HTTPException(400, "수정 가능한 필드 없음")
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            sets = ", ".join(f"{k} = ?" for k in update)
            vals = list(update.values()) + [candidate_id]
            conn.execute(
                f"UPDATE candidates SET {sets} WHERE candidate_id = ?", vals
            )
            conn.commit()
            return ok(message="수정 완료")
        finally:
            conn.close()
    except Exception as e:
        import logging as _log_upd
        _log_upd.getLogger("bridge.api").error("admin_update 실패: %s", e, exc_info=True)
        err("수정에 실패했습니다.", 500)


@app.delete("/api/admin/candidates/{candidate_id}", tags=["admin"])
async def admin_delete_candidate(candidate_id: str, request: Request):
    """Soft Delete — status='Deleted' 설정 (물리 삭제 금지)."""
    _check_admin(request)
    try:
        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            conn.execute(
                "UPDATE candidates SET status = 'Deleted', updated_at = ? WHERE candidate_id = ?",
                (datetime.now(timezone.utc).isoformat(), candidate_id),
            )
            conn.commit()
            return ok(message="삭제 처리 완료 (soft delete)")
        finally:
            conn.close()
    except Exception as e:
        import logging as _log_del
        _log_del.getLogger("bridge.api").error("admin_delete 실패: %s", e, exc_info=True)
        err("삭제에 실패했습니다.", 500)


@app.put("/api/admin/candidates/{candidate_id}", tags=["admin"])
async def admin_full_update_candidate(candidate_id: str, request: Request, body: dict):
    """지원자 모든 컬럼 수정 (관리자 전용)."""
    _check_admin(request)
    # candidate_id, created_at는 수정 불가
    body.pop("candidate_id", None)
    body.pop("id", None)
    body.pop("created_at", None)
    if not body:
        raise HTTPException(400, "수정할 데이터 없음")
    body["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            sets = ", ".join(f"{k} = ?" for k in body)
            vals = list(body.values()) + [candidate_id]
            conn.execute(f"UPDATE candidates SET {sets} WHERE candidate_id = ?", vals)
            conn.commit()
            return ok(message="수정 완료")
        finally:
            conn.close()
    except Exception as e:
        import logging as _log_ful
        _log_ful.getLogger("bridge.api").error("admin_full_update 실패: %s", e, exc_info=True)
        err("수정에 실패했습니다.", 500)


class BulkStatusBody(BaseModel):
    ids: list[str]
    status: str = Field(..., min_length=1, max_length=50)


@app.put("/api/admin/candidates/bulk-status", tags=["admin"])
async def admin_bulk_status(request: Request, body: BulkStatusBody):
    """여러 지원자 상태 일괄 변경."""
    _check_admin(request)
    if not body.ids:
        raise HTTPException(400, "대상 ID 목록 필요")
    try:
        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            placeholders = ",".join("?" * len(body.ids))
            conn.execute(
                f"UPDATE candidates SET status = ?, updated_at = ? WHERE candidate_id IN ({placeholders})",
                [body.status, now_iso] + body.ids,
            )
            conn.commit()
            return ok(message=f"{len(body.ids)}명 상태 → {body.status}")
        finally:
            conn.close()
    except Exception as e:
        import logging as _log_bulk
        _log_bulk.getLogger("bridge.api").error("bulk_status 실패: %s", e, exc_info=True)
        err("일괄 상태 변경에 실패했습니다.", 500)


@app.get("/api/admin/candidates/{candidate_id}/profile", tags=["admin"])
async def admin_candidate_profile(candidate_id: str, request: Request):
    """후보자 프로필 카드 HTML 미리보기 (PII 제외)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="후보자를 찾을 수 없습니다.")
        c = dict(row)
        c["id"] = c.get("candidate_id", c.get("id", ""))
        card_html = _build_profile_card(c)
        return ok(data={"html": card_html, "candidate_id": candidate_id})
    finally:
        conn.close()


# ── Admin: Inquiries (채용의뢰) 관리 ────────────────────────────────────────

@app.get("/api/admin/inquiries", tags=["admin"])
async def admin_list_inquiries(request: Request, limit: int = 200, offset: int = 0):
    """채용의뢰 목록 — client_inquiries 테이블."""
    _check_admin(request)
    try:
        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.row_factory = sqlite3.Row
        try:
            total = conn.execute("SELECT COUNT(*) FROM client_inquiries").fetchone()[0]
            rows = conn.execute(
                "SELECT * FROM client_inquiries ORDER BY submitted_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return ok(data={"total": total, "inquiries": [dict(r) for r in rows]})
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        import logging as _log_inq
        _log_inq.getLogger("bridge.api").error("admin_inquiries 실패: %s", e, exc_info=True)
        err("채용의뢰 목록을 불러올 수 없습니다.", 500)


@app.put("/api/admin/inquiries/{inquiry_id}", tags=["admin"])
async def admin_update_inquiry(inquiry_id: int, request: Request, body: dict):
    """채용의뢰 상태/메모 수정."""
    _check_admin(request)
    EDITABLE = {"inbox_status", "notes", "assigned_to"}
    update = {k: v for k, v in body.items() if k in EDITABLE}
    if not update:
        raise HTTPException(400, "수정 가능한 필드: inbox_status, notes, assigned_to")
    update["last_activity"] = datetime.now(timezone.utc).isoformat()
    try:
        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            sets = ", ".join(f"{k} = ?" for k in update)
            vals = list(update.values()) + [inquiry_id]
            conn.execute(f"UPDATE client_inquiries SET {sets} WHERE id = ?", vals)
            conn.commit()
            return ok(message="수정 완료")
        finally:
            conn.close()
    except Exception as e:
        import logging as _log_upd
        _log_upd.getLogger("bridge.api").error("admin_update_inquiry 실패: %s", e, exc_info=True)
        err("수정에 실패했습니다.", 500)


# ── Admin: Email Templates & Guide Links ────────────────────────────────────

@app.get("/api/admin/email-templates", tags=["admin"])
async def admin_list_email_templates(request: Request):
    """이메일 템플릿 목록."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM email_templates ORDER BY template_key").fetchall()
        return ok(data=[dict(r) for r in rows])
    finally:
        conn.close()


@app.put("/api/admin/email-templates/{template_key}", tags=["admin"])
async def admin_update_email_template(template_key: str, request: Request, body: dict):
    """이메일 템플릿 수정/생성."""
    _check_admin(request)
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    try:
        conn.execute(
            """INSERT INTO email_templates (template_key, subject, body_html, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(template_key) DO UPDATE SET
                 subject = excluded.subject,
                 body_html = excluded.body_html,
                 updated_at = excluded.updated_at""",
            (template_key, body.get("subject", ""), body.get("body_html", ""), now_iso),
        )
        conn.commit()
        return ok(message=f"템플릿 '{template_key}' 저장 완료")
    finally:
        conn.close()


@app.get("/api/admin/guide-links", tags=["admin"])
async def admin_list_guide_links(request: Request):
    """가이드 링크 목록."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM guide_links ORDER BY link_key").fetchall()
        return ok(data=[dict(r) for r in rows])
    finally:
        conn.close()


@app.put("/api/admin/guide-links/{link_key}", tags=["admin"])
async def admin_update_guide_link(link_key: str, request: Request, body: dict):
    """가이드 링크 수정/생성."""
    _check_admin(request)
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    try:
        conn.execute(
            """INSERT INTO guide_links (link_key, url, label, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(link_key) DO UPDATE SET
                 url = excluded.url,
                 label = excluded.label,
                 updated_at = excluded.updated_at""",
            (link_key, body.get("url", ""), body.get("label", ""), now_iso),
        )
        conn.commit()
        return ok(message=f"링크 '{link_key}' 저장 완료")
    finally:
        conn.close()


# ── Email Sending API ────────────────────────────────────────────────────────
import smtplib
import ssl as _ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

_SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
_SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
_SMTP_USER = os.getenv("SMTP_USER", os.getenv("GMAIL_USER", ""))
_SMTP_PASS = os.getenv("SMTP_PASS", os.getenv("GMAIL_APP_PASSWORD", ""))
_log_email = logging.getLogger("bridge.email_send")

# template_key → candidates 컬럼 매핑
_TEMPLATE_COL_MAP = {
    "contract_offer":       "email_contract",
    "immigration_guide":    "email_immigration",
    "overseas_visa_prep":   "email_overseas",
    "job_transition_guide": "email_transition",
    "arrival_guide":        "email_arrival",
}


def _smtp_send(to_email: str, subject: str, html_body: str) -> bool:
    """Gmail SMTP로 이메일 발송. 실패 시 False."""
    if not _SMTP_USER or not _SMTP_PASS or _SMTP_PASS == "your_app_password":
        _log_email.warning("SMTP 미설정 — 발송 스킵 (to=%s)", to_email)
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"BRIDGE Recruitment <{_SMTP_USER}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        ctx = _ssl.create_default_context()
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as srv:
            srv.ehlo()
            srv.starttls(context=ctx)
            srv.ehlo()
            srv.login(_SMTP_USER, _SMTP_PASS)
            srv.sendmail(_SMTP_USER, to_email, msg.as_string())

        _log_email.info("이메일 발송 성공: %s → %s", subject[:40], to_email)
        return True
    except Exception as e:
        _log_email.error("이메일 발송 실패 (to=%s): %s", to_email, e, exc_info=True)
        return False


def _load_guide_links(conn: sqlite3.Connection) -> dict:
    """guide_links 테이블에서 link_key→url 딕셔너리 로드."""
    try:
        rows = conn.execute("SELECT link_key, url FROM guide_links").fetchall()
        return {r[0]: r[1] for r in rows}
    except Exception:
        return {}


def _substitute_vars(html: str, candidate: dict, guide_links: dict) -> str:
    """{{변수}} 치환: candidate 필드 + guide_links + 날짜."""
    # candidate 필드 치환
    field_map = {
        "name": candidate.get("full_name") or candidate.get("first_name", ""),
        "email": candidate.get("email", ""),
        "company": candidate.get("placed_company", ""),
        "location": candidate.get("city") or candidate.get("location", ""),
        "salary": candidate.get("placed_salary") or candidate.get("desired_salary", ""),
        "start_date": candidate.get("start_month") or candidate.get("start_detail", ""),
        "housing": candidate.get("housing_type") or candidate.get("housing_detail", ""),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "recruiter_name": candidate.get("assigned_to", "BRIDGE"),
    }
    for key, val in field_map.items():
        html = html.replace("{{" + key + "}}", str(val or ""))

    # guide_links 치환: {{link_xxx}} → guide_links[xxx] URL
    for link_key, url in guide_links.items():
        html = html.replace("{{link_" + link_key + "}}", url)

    # 미치환 {{link_xxx}} 제거 (# 링크로 대체)
    html = re.sub(r"\{\{link_\w+\}\}", "#", html)
    # 미치환 {{xxx}} 제거
    html = re.sub(r"\{\{\w+\}\}", "", html)

    return html


def _build_profile_card(c: dict) -> str:
    """PII 제외 후보자 프로필 카드 HTML 생성."""
    cid = c.get("id", "")
    nationality = c.get("nationality", "—")
    visa = c.get("visa_type", "—")
    age = c.get("age", "—")
    education = c.get("education_level", "—")
    teaching_exp = c.get("teaching_experience", "—")
    korea_exp = c.get("korea_experience", "—")
    location = c.get("city", "—")
    available = c.get("start_month") or c.get("available_from", "—")
    photo = c.get("photo_url", "")

    photo_html = ""
    if photo:
        photo_html = f'<img src="{photo}" style="width:80px;height:80px;border-radius:50%;object-fit:cover" alt="photo"/>'

    return f"""<div style="border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin:12px 0;display:flex;gap:16px;align-items:flex-start">
  {photo_html}
  <div style="flex:1;font-size:14px">
    <p style="font-weight:bold;font-size:15px;margin:0 0 8px">ID #{cid} · {nationality}</p>
    <table style="font-size:13px;border-collapse:collapse;width:100%">
      <tr><td style="color:#6b7280;padding:2px 12px 2px 0">Visa</td><td>{visa}</td></tr>
      <tr><td style="color:#6b7280;padding:2px 12px 2px 0">Age</td><td>{age}</td></tr>
      <tr><td style="color:#6b7280;padding:2px 12px 2px 0">Education</td><td>{education}</td></tr>
      <tr><td style="color:#6b7280;padding:2px 12px 2px 0">Teaching Exp.</td><td>{teaching_exp}</td></tr>
      <tr><td style="color:#6b7280;padding:2px 12px 2px 0">Korea Exp.</td><td>{korea_exp}</td></tr>
      <tr><td style="color:#6b7280;padding:2px 12px 2px 0">Location</td><td>{location}</td></tr>
      <tr><td style="color:#6b7280;padding:2px 12px 2px 0">Available</td><td>{available}</td></tr>
    </table>
  </div>
</div>"""


class SendEmailBody(BaseModel):
    template_key: str
    custom_subject: Optional[str] = None
    custom_body: Optional[str] = None


@app.post("/api/admin/candidates/{candidate_id}/send-email", tags=["admin"])
async def admin_send_email(candidate_id: int, request: Request, body: SendEmailBody):
    """후보자에게 이메일 템플릿 발송. template_key에 따라 해당 email_* 컬럼 업데이트."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        # 후보자 조회
        row = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="후보자를 찾을 수 없습니다.")
        c = dict(row)

        # 이메일 주소 복호화
        to_email = c.get("email", "")
        if to_email and is_encrypted(to_email):
            to_email = decrypt_field(to_email)
        if not to_email or "@" not in to_email:
            raise HTTPException(status_code=400, detail="유효한 이메일 주소가 없습니다.")

        # 이름 복호화 (변수 치환용)
        for f in ("full_name", "first_name", "last_name", "phone"):
            val = c.get(f, "")
            if val and is_encrypted(val):
                c[f] = decrypt_field(val)

        # 커스텀 내용 또는 템플릿 로드
        if body.custom_subject and body.custom_body:
            subject = body.custom_subject
            html = body.custom_body
        else:
            tpl = conn.execute(
                "SELECT subject, body_html FROM email_templates WHERE template_key = ?",
                (body.template_key,)
            ).fetchone()
            if not tpl:
                raise HTTPException(status_code=404, detail=f"템플릿 '{body.template_key}'을 찾을 수 없습니다.")
            subject = body.custom_subject or tpl["subject"]
            html = body.custom_body or tpl["body_html"]

        # 변수 치환
        guide_links = _load_guide_links(conn)
        html = _substitute_vars(html, c, guide_links)
        subject = _substitute_vars(subject, c, guide_links)

        # 발송
        sent = _smtp_send(to_email, subject, html)
        if not sent:
            raise HTTPException(status_code=500, detail="이메일 발송에 실패했습니다. SMTP 설정을 확인하세요.")

        # 발송 기록: 해당 email_* 컬럼 업데이트
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        col = _TEMPLATE_COL_MAP.get(body.template_key)
        if col:
            conn.execute(f"UPDATE candidates SET {col} = ? WHERE id = ?", (now_iso, candidate_id))
            conn.commit()

        return ok(message=f"이메일 발송 완료 → {to_email}", data={"sent_to": to_email, "template": body.template_key})
    finally:
        conn.close()


class BulkSendBody(BaseModel):
    candidate_ids: list[int]
    template_key: str


@app.post("/api/admin/candidates/bulk-send", tags=["admin"])
async def admin_bulk_send(request: Request, body: BulkSendBody):
    """다수 후보자에게 일괄 이메일 발송 (1초 간격)."""
    _check_admin(request)
    import asyncio

    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        # 템플릿 로드
        tpl = conn.execute(
            "SELECT subject, body_html FROM email_templates WHERE template_key = ?",
            (body.template_key,)
        ).fetchone()
        if not tpl:
            raise HTTPException(status_code=404, detail=f"템플릿 '{body.template_key}'을 찾을 수 없습니다.")

        guide_links = _load_guide_links(conn)
        results = []

        for cid in body.candidate_ids:
            row = conn.execute("SELECT * FROM candidates WHERE id = ?", (cid,)).fetchone()
            if not row:
                results.append({"id": cid, "status": "not_found"})
                continue
            c = dict(row)

            # 이메일 복호화
            to_email = c.get("email", "")
            if to_email and is_encrypted(to_email):
                to_email = decrypt_field(to_email)
            if not to_email or "@" not in to_email:
                results.append({"id": cid, "status": "no_email"})
                continue

            # 이름 복호화
            for f in ("full_name", "first_name", "last_name", "phone"):
                val = c.get(f, "")
                if val and is_encrypted(val):
                    c[f] = decrypt_field(val)

            # 치환 + 발송
            subject = _substitute_vars(tpl["subject"], c, guide_links)
            html = _substitute_vars(tpl["body_html"], c, guide_links)
            sent = _smtp_send(to_email, subject, html)

            if sent:
                now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                col = _TEMPLATE_COL_MAP.get(body.template_key)
                if col:
                    conn.execute(f"UPDATE candidates SET {col} = ? WHERE id = ?", (now_iso, cid))
                results.append({"id": cid, "status": "sent"})
            else:
                results.append({"id": cid, "status": "failed"})

            # 1초 간격 (스팸 방지)
            await asyncio.sleep(1)

        conn.commit()
        sent_count = sum(1 for r in results if r["status"] == "sent")
        return ok(
            message=f"일괄 발송 완료: {sent_count}/{len(body.candidate_ids)}건 성공",
            data={"results": results}
        )
    finally:
        conn.close()


class SendProfilesBody(BaseModel):
    candidate_ids: list[int]
    to_email: str
    school_name: Optional[str] = None


@app.post("/api/admin/candidates/send-profiles", tags=["admin"])
async def admin_send_profiles(request: Request, body: SendProfilesBody):
    """학교에 후보자 프로필 카드 발송 (PII 제외)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        # candidate_profile 템플릿 로드
        tpl = conn.execute(
            "SELECT subject, body_html FROM email_templates WHERE template_key = 'candidate_profile'"
        ).fetchone()
        if not tpl:
            raise HTTPException(status_code=404, detail="candidate_profile 템플릿이 없습니다.")

        # 프로필 카드 생성
        cards_html = ""
        for cid in body.candidate_ids:
            row = conn.execute("SELECT * FROM candidates WHERE id = ?", (cid,)).fetchone()
            if not row:
                continue
            c = dict(row)
            # PII 필드는 프로필 카드에 포함하지 않음 (이름, 이메일, 전화번호 제외)
            cards_html += _build_profile_card(c)

        if not cards_html:
            raise HTTPException(status_code=400, detail="유효한 후보자가 없습니다.")

        # 템플릿에 프로필 카드 삽입
        guide_links = _load_guide_links(conn)
        html = tpl["body_html"].replace("{{profile_cards}}", cards_html)
        subject = tpl["subject"]

        # 학교명이 있으면 제목에 추가
        if body.school_name:
            subject = f"{subject} - {body.school_name}"

        # 미치환 변수 정리
        html = re.sub(r"\{\{\w+\}\}", "", html)

        sent = _smtp_send(body.to_email, subject, html)
        if not sent:
            raise HTTPException(status_code=500, detail="이메일 발송에 실패했습니다.")

        return ok(
            message=f"프로필 발송 완료 → {body.to_email} ({len(body.candidate_ids)}명)",
            data={"sent_to": body.to_email, "candidate_count": len(body.candidate_ids)}
        )
    finally:
        conn.close()


# ── Community Board API ──────────────────────────────────────────────────────
_BOARDS = {"visa", "support_kr", "support", "about", "korea", "tips", "testimonials", "information"}
_RATE_LIMIT: dict[str, list] = {}  # ip_hash → [timestamps]

import hashlib, time as _time

def _ip_hash(request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    return hashlib.sha256(ip.encode()).hexdigest()[:16]

def _rate_ok(ip_hash: str, window: int = 300, max_posts: int = 5) -> bool:
    """5분 안에 최대 5건 포스팅 허용 (IP 해시 기반)."""
    now = _time.time()
    ts = _RATE_LIMIT.get(ip_hash, [])
    ts = [t for t in ts if now - t < window]
    if len(ts) >= max_posts:
        return False
    ts.append(now)
    _RATE_LIMIT[ip_hash] = ts
    return True


@app.get("/api/community/{board}", tags=["community"])
async def community_list(
    board: str,
    limit: int = 30,
    offset: int = 0,
):
    if board not in _BOARDS:
        raise HTTPException(404, "Board not found")
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT id, title, author_hash, pinned, views, created_at,
                  substr(body, 1, 200) AS preview
           FROM community_posts
           WHERE board=? AND is_deleted=0
           ORDER BY pinned DESC, created_at DESC
           LIMIT ? OFFSET ?""",
        (board, limit, offset),
    ).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) FROM community_posts WHERE board=? AND is_deleted=0", (board,)
    ).fetchone()[0]
    conn.close()
    return ok(data={"total": total, "posts": [dict(r) for r in rows]})


@app.get("/api/community/{board}/{post_id}", tags=["community"])
async def community_get(board: str, post_id: int):
    if board not in _BOARDS:
        raise HTTPException(404, "Board not found")
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute(
        "UPDATE community_posts SET views=views+1 WHERE id=? AND board=? AND is_deleted=0",
        (post_id, board),
    )
    conn.commit()
    row = conn.execute(
        """SELECT id, board, title, body, pinned, views, created_at
           FROM community_posts WHERE id=? AND board=? AND is_deleted=0""",
        (post_id, board),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Post not found")
    return ok(data=dict(row))


class CommunityPost(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    body:  str = Field(..., min_length=10, max_length=10000)


@app.post("/api/community/{board}", status_code=201, tags=["community"])
async def community_create(board: str, post: CommunityPost, request: Request):
    if board not in _BOARDS:
        raise HTTPException(404, "Board not found")
    ip_hash = _ip_hash(request)
    if not _rate_ok(ip_hash):
        raise HTTPException(429, "Too many posts. Please wait a few minutes.")

    # HTML 태그 strip (Stored XSS 방지)
    _tag_re = re.compile(r'<[^>]+>')
    clean_title = _tag_re.sub('', post.title.strip())
    clean_body = _tag_re.sub('', post.body.strip())

    # 게시글 본문에서 연락처 PII 차단
    _pii_check = re.compile(r'01[016789][- ]?\d{3,4}[- ]?\d{4}|[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
    if _pii_check.search(clean_body) or _pii_check.search(clean_title):
        raise HTTPException(400, "Phone numbers and email addresses are not allowed in posts.")

    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    cur = conn.execute(
        "INSERT INTO community_posts (board, title, body, author_hash) VALUES (?,?,?,?)",
        (board, clean_title, clean_body, ip_hash),
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return ok(data={"id": new_id}, message="Post created")


@app.delete("/api/community/{board}/{post_id}", tags=["community"])
async def community_delete(board: str, post_id: int, request: Request):
    """작성자(IP 해시 일치)만 삭제 가능."""
    if board not in _BOARDS:
        raise HTTPException(404, "Board not found")
    ip_hash = _ip_hash(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    r = conn.execute(
        "SELECT author_hash FROM community_posts WHERE id=? AND board=? AND is_deleted=0",
        (post_id, board),
    ).fetchone()
    if not r:
        conn.close(); raise HTTPException(404, "Post not found")
    is_admin = _ADMIN_KEY and request.headers.get("x-admin-key", "") == _ADMIN_KEY
    if r[0] != ip_hash and not is_admin:
        conn.close(); raise HTTPException(403, "Forbidden")
    conn.execute("UPDATE community_posts SET is_deleted=1 WHERE id=?", (post_id,))
    conn.commit(); conn.close()
    return ok(message="Deleted")


# ── Admin: Community Posts 관리 ────────────────────────────────────────────────

class PinUpdate(BaseModel):
    pinned: int = Field(..., ge=0, le=1)


@app.patch("/api/admin/community/posts/{post_id}/pin", tags=["admin"])
async def admin_pin_post(post_id: int, body: PinUpdate, request: Request):
    """게시글 고정/해제 (관리자 전용)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    r = conn.execute(
        "SELECT id FROM community_posts WHERE id=? AND is_deleted=0", (post_id,)
    ).fetchone()
    if not r:
        conn.close(); raise HTTPException(404, "Post not found")
    conn.execute("UPDATE community_posts SET pinned=? WHERE id=?", (body.pinned, post_id))
    conn.commit(); conn.close()
    return ok(message=f"Post #{post_id} pinned={body.pinned}")


class PostEdit(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    body:  Optional[str] = Field(None, min_length=10, max_length=10000)


@app.patch("/api/admin/community/{board}/{post_id}", tags=["admin"])
async def admin_edit_post(board: str, post_id: int, body: PostEdit, request: Request):
    """게시글 제목/본문 수정 (관리자 전용)."""
    _check_admin(request)
    if board not in _BOARDS:
        raise HTTPException(404, "Board not found")

    _tag_re = re.compile(r'<[^>]+>')
    updates: list[str] = []
    params: list = []
    if body.title is not None:
        updates.append("title = ?")
        params.append(_tag_re.sub('', body.title.strip()))
    if body.body is not None:
        updates.append("body = ?")
        params.append(_tag_re.sub('', body.body.strip()))

    if not updates:
        raise HTTPException(400, "수정할 항목이 없습니다.")

    params.extend([post_id, board])
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        r = conn.execute(
            "SELECT id FROM community_posts WHERE id=? AND board=? AND is_deleted=0",
            (post_id, board),
        ).fetchone()
        if not r:
            raise HTTPException(404, "Post not found")
        conn.execute(
            f"UPDATE community_posts SET {', '.join(updates)} WHERE id=? AND board=?",
            params,
        )
        conn.commit()
    finally:
        conn.close()
    return ok(message=f"Post #{post_id} updated")


@app.get("/api/admin/community/posts", tags=["admin"])
async def admin_search_posts(
    request: Request,
    search: Optional[str] = None,
    board: Optional[str] = None,
    limit: int = 200,
):
    """관리자 게시글 검색 (전체 보드 대상)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        where_parts = ["is_deleted=0"]
        params: list = []
        if board and board != "all":
            if board not in _BOARDS:
                raise HTTPException(404, "Board not found")
            where_parts.append("board=?")
            params.append(board)
        if search:
            where_parts.append("(title LIKE ? OR body LIKE ?)")
            term = f"%{search}%"
            params.extend([term, term])

        where = " AND ".join(where_parts)
        params.append(limit)
        rows = conn.execute(
            f"""SELECT id, board, title, author_hash, pinned, views, created_at,
                       substr(body, 1, 200) AS preview
                FROM community_posts
                WHERE {where}
                ORDER BY pinned DESC, created_at DESC
                LIMIT ?""",
            params,
        ).fetchall()
        return ok(data={"posts": [dict(r) for r in rows]})
    finally:
        conn.close()


# ── Admin: Applications 관리 ─────────────────────────────────────────────────

@app.get("/api/admin/applications", tags=["admin"])
async def admin_list_applications(request: Request):
    """구직자 + 구인자 접수 통합 목록 — SQLite."""
    _check_admin(request)
    try:
        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.row_factory = sqlite3.Row
        try:
            apps: list[dict] = []

            # 구직자 (candidates)
            cands = conn.execute(
                "SELECT candidate_id, full_name, email, status, created_at, updated_at "
                "FROM candidates ORDER BY created_at DESC LIMIT 200"
            ).fetchall()
            for c in cands:
                apps.append({
                    "id": c["candidate_id"], "type": "candidate",
                    "name": c["full_name"] or "", "email": c["email"] or "",
                    "status": c["status"] or "Active",
                    "created_at": c["created_at"] or "",
                    "updated_at": c["updated_at"],
                })

            # 구인자 (client_inquiries)
            inqs = conn.execute(
                "SELECT id, school_name, contact_name, email, inbox_status, submitted_at "
                "FROM client_inquiries ORDER BY submitted_at DESC LIMIT 200"
            ).fetchall()
            for i in inqs:
                apps.append({
                    "id": str(i["id"]), "type": "employer",
                    "name": i["contact_name"] or "", "email": i["email"] or "",
                    "school_name": i["school_name"] or "",
                    "status": i["inbox_status"] or "pending",
                    "created_at": i["submitted_at"] or "",
                })

            apps.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return ok(data=apps)
        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        import logging as _log_apps
        _log_apps.getLogger("bridge.api").error("admin_applications 실패: %s", e, exc_info=True)
        err("접수 목록을 불러올 수 없습니다.", 500)


class StatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)
    type: Optional[str] = None


@app.patch("/api/admin/applications/{app_id}", tags=["admin"])
async def admin_update_application(app_id: str, body: StatusUpdate, request: Request):
    """접수 상태 변경 — SQLite."""
    _check_admin(request)
    try:
        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            if body.type == "candidate":
                conn.execute(
                    "UPDATE candidates SET status = ?, updated_at = ? WHERE candidate_id = ?",
                    (body.status, now_iso, app_id),
                )
            else:
                conn.execute(
                    "UPDATE client_inquiries SET inbox_status = ?, last_activity = ? WHERE id = ?",
                    (body.status, now_iso, int(app_id)),
                )
            conn.commit()
            return ok(message=f"{app_id} → {body.status}")
        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        import logging as _log_upd
        _log_upd.getLogger("bridge.api").error("admin_update_app 실패: %s", e, exc_info=True)
        err("상태 변경에 실패했습니다.", 500)


# ── Admin: Payments 관리 ──────────────────────────────────────────────────────

@app.get("/api/admin/payments", tags=["admin"])
async def admin_list_payments(request: Request):
    """결제 기록 목록 — SQLite (테이블 없으면 빈 배열)."""
    _check_admin(request)
    try:
        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.row_factory = sqlite3.Row
        try:
            # payments 테이블 존재 여부 확인
            exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='payments'"
            ).fetchone()
            if not exists:
                return ok(data=[])
            rows = conn.execute(
                "SELECT * FROM payments ORDER BY created_at DESC LIMIT 200"
            ).fetchall()
            return ok(data=[dict(r) for r in rows])
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        import logging as _log_pay
        _log_pay.getLogger("bridge.api").error("admin_payments 실패: %s", e, exc_info=True)
        return ok(data=[])


class PaymentStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)


@app.patch("/api/admin/payments/{payment_id}", tags=["admin"])
async def admin_update_payment(payment_id: str, body: PaymentStatusUpdate, request: Request):
    """결제 상태 변경."""
    _check_admin(request)
    try:
        sb = get_svc_client()
        now_iso = datetime.now(timezone.utc).isoformat()
        sb.table("payments").update({
            "status": body.status,
            "confirmed_at": now_iso if body.status == "confirmed" else None,
            "updated_at": now_iso,
        }).eq("id", payment_id).execute()
        return ok(message=f"Payment {payment_id} → {body.status}")

    except HTTPException:
        raise
    except Exception as e:
        import logging as _log_pay_upd
        _log_pay_upd.getLogger("bridge.api").error("admin_payment_update 실패: %s", e, exc_info=True)
        err("상태 변경에 실패했습니다.", 500)


# ── Admin: Interview Scheduling ──────────────────────────────────────────────

class InterviewCreate(BaseModel):
    candidate_name:  str = Field("", max_length=200)
    candidate_email: str = Field("", max_length=200)
    employer_name:   str = Field("", max_length=200)
    employer_email:  str = Field("", max_length=200)
    interview_date:  str = Field(..., min_length=8, max_length=20)
    interview_time:  str = Field(..., min_length=3, max_length=20)
    meet_link:       str = Field(..., min_length=5, max_length=500)
    notes:           str = Field("", max_length=2000)
    send_email:      bool = True


@app.get("/api/admin/interviews", tags=["admin"])
async def admin_list_interviews(request: Request, status: Optional[str] = None):
    """인터뷰 목록 조회."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    if status:
        rows = conn.execute(
            "SELECT * FROM interviews WHERE is_deleted=0 AND status=? ORDER BY interview_date DESC, interview_time DESC",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM interviews WHERE is_deleted=0 ORDER BY interview_date DESC, interview_time DESC"
        ).fetchall()
    conn.close()
    return ok(data=[dict(r) for r in rows])


@app.post("/api/admin/interviews", status_code=201, tags=["admin"])
async def admin_create_interview(body: InterviewCreate, request: Request):
    """인터뷰 생성 + 이메일 자동 발송."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    cur = conn.execute(
        """INSERT INTO interviews
           (candidate_name, candidate_email, employer_name, employer_email,
            interview_date, interview_time, meet_link, notes)
           VALUES (?,?,?,?,?,?,?,?)""",
        (body.candidate_name, body.candidate_email,
         body.employer_name, body.employer_email,
         body.interview_date, body.interview_time,
         body.meet_link, body.notes),
    )
    interview_id = cur.lastrowid
    conn.commit()

    # 이메일 자동 발송
    email_results = {"candidate": False, "employer": False}
    if body.send_email and _EMAIL_OK:
        try:
            from email_templates import send_interview_invitation, send_interview_invitation_employer
            if body.candidate_email:
                email_results["candidate"] = send_interview_invitation(
                    body.candidate_email, body.candidate_name or "Candidate",
                    body.interview_date, body.interview_time,
                    body.meet_link, body.employer_name,
                )
                if email_results["candidate"]:
                    conn.execute("UPDATE interviews SET email_sent_candidate=1 WHERE id=?", (interview_id,))
            if body.employer_email:
                email_results["employer"] = send_interview_invitation_employer(
                    body.employer_email, body.employer_name or "담당자",
                    body.interview_date, body.interview_time,
                    body.meet_link, body.candidate_name,
                )
                if email_results["employer"]:
                    conn.execute("UPDATE interviews SET email_sent_employer=1 WHERE id=?", (interview_id,))
            conn.commit()
        except Exception as e:
            import logging as _log_iv
            _log_iv.getLogger("bridge.api").error("인터뷰 이메일 발송 실패: %s", e, exc_info=True)

    conn.close()
    return ok(
        data={"id": interview_id, "email_sent": email_results},
        message=f"Interview #{interview_id} created",
    )


class InterviewStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=20)


@app.patch("/api/admin/interviews/{interview_id}", tags=["admin"])
async def admin_update_interview(interview_id: int, body: InterviewStatusUpdate, request: Request):
    """인터뷰 상태 변경."""
    _check_admin(request)
    valid = {"scheduled", "completed", "cancelled", "no_show"}
    if body.status not in valid:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid}")
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    r = conn.execute("SELECT id FROM interviews WHERE id=? AND is_deleted=0", (interview_id,)).fetchone()
    if not r:
        conn.close()
        raise HTTPException(404, "Interview not found")
    conn.execute(
        "UPDATE interviews SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (body.status, interview_id),
    )
    conn.commit()
    conn.close()
    return ok(message=f"Interview #{interview_id} → {body.status}")


@app.delete("/api/admin/interviews/{interview_id}", tags=["admin"])
async def admin_delete_interview(interview_id: int, request: Request):
    """인터뷰 삭제 (soft delete)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    r = conn.execute("SELECT id FROM interviews WHERE id=? AND is_deleted=0", (interview_id,)).fetchone()
    if not r:
        conn.close()
        raise HTTPException(404, "Interview not found")
    conn.execute("UPDATE interviews SET is_deleted=1, updated_at=CURRENT_TIMESTAMP WHERE id=?", (interview_id,))
    conn.commit()
    conn.close()
    return ok(message=f"Interview #{interview_id} deleted")


# ── File Upload System ─────────────────────────────────────────────────────────
_UPLOAD_BASE = Path(os.getenv("BRIDGE_UPLOAD_DIR", str(Path(__file__).resolve().parent / "uploads")))
_UPLOAD_BASE.mkdir(parents=True, exist_ok=True)

_log_upload = logging.getLogger("bridge.upload")

# File type configs: (max_bytes, allowed_extensions, magic_bytes_prefixes)
_FILE_LIMITS: dict[str, tuple[int, set[str], list[bytes]]] = {
    "photo": (
        5 * 1024 * 1024,
        {".jpg", ".jpeg", ".png", ".webp"},
        [b"\xff\xd8\xff", b"\x89PNG", b"RIFF"],  # JPEG, PNG, WebP
    ),
    "cv": (
        10 * 1024 * 1024,
        {".pdf", ".doc", ".docx"},
        [b"%PDF", b"\xd0\xcf\x11\xe0", b"PK"],  # PDF, DOC, DOCX
    ),
    "cover_letter": (
        10 * 1024 * 1024,
        {".pdf", ".doc", ".docx"},
        [b"%PDF", b"\xd0\xcf\x11\xe0", b"PK"],
    ),
    "certificate": (
        10 * 1024 * 1024,
        {".pdf", ".jpg", ".jpeg", ".png"},
        [b"%PDF", b"\xff\xd8\xff", b"\x89PNG"],
    ),
    "video": (
        100 * 1024 * 1024,
        {".mp4", ".mov", ".webm"},
        [],  # skip magic for video (too many codecs)
    ),
    "attachment": (
        10 * 1024 * 1024,
        {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"},
        [b"%PDF", b"\xd0\xcf\x11\xe0", b"PK", b"\xff\xd8\xff", b"\x89PNG"],
    ),
}


def _validate_file(data: bytes, filename: str, file_type: str) -> str:
    """Validate file extension and magic bytes. Returns sanitized extension."""
    cfg = _FILE_LIMITS.get(file_type)
    if not cfg:
        raise HTTPException(400, f"Unknown file type: {file_type}")

    max_size, allowed_ext, magic_prefixes = cfg
    if len(data) > max_size:
        raise HTTPException(413, f"File too large. Max {max_size // (1024*1024)}MB for {file_type}.")

    ext = Path(filename).suffix.lower()
    if ext not in allowed_ext:
        raise HTTPException(400, f"Invalid file extension '{ext}'. Allowed: {', '.join(sorted(allowed_ext))}")

    if magic_prefixes and not any(data[:8].startswith(m) for m in magic_prefixes):
        raise HTTPException(400, "File content does not match its extension.")

    return ext


def _make_thumbnail(src_path: Path, thumb_path: Path, size: int = 150) -> bool:
    """Create a 150x150 top-center crop thumbnail for portrait photos."""
    if not _PILLOW_OK:
        return False
    try:
        with PILImage.open(src_path) as img:
            img = img.convert("RGB")
            w, h = img.size
            # Crop square from top-center with 15% vertical offset
            sq = min(w, h)
            left = (w - sq) // 2
            top = int(h * 0.15)  # 15% offset for face area
            if top + sq > h:
                top = max(0, h - sq)
            img_crop = img.crop((left, top, left + sq, top + sq))
            img_crop = img_crop.resize((size, size), PILImage.LANCZOS)
            img_crop.save(thumb_path, "JPEG", quality=85)
        return True
    except Exception as e:
        _log_upload.error("Thumbnail generation failed: %s", e)
        return False


@app.post("/api/upload/{entity_type}/{entity_id}", tags=["upload"])
async def upload_file(
    entity_type: str,
    entity_id: str,
    request: Request,
    file: UploadFile = FastFile(...),
    file_type: str = "attachment",
):
    """
    파일 업로드 엔드포인트.
    entity_type: 'candidate' | 'inquiry'
    file_type: 'photo' | 'cv' | 'cover_letter' | 'certificate' | 'video' | 'attachment'
    """
    if entity_type not in ("candidate", "inquiry"):
        raise HTTPException(400, "entity_type must be 'candidate' or 'inquiry'")

    if not _rate_ok(_ip_hash(request), window=60, max_posts=30):
        raise HTTPException(429, "Too many uploads. Please slow down.")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file.")

    ext = _validate_file(data, file.filename or "file", file_type)

    # Build directory
    dir_name = "candidates" if entity_type == "candidate" else "inquiries"
    if file_type == "certificate":
        entity_dir = _UPLOAD_BASE / dir_name / entity_id / "certificates"
    else:
        entity_dir = _UPLOAD_BASE / dir_name / entity_id
    entity_dir.mkdir(parents=True, exist_ok=True)

    # File naming
    if file_type == "photo":
        fname = f"photo_original{ext}"
    elif file_type in ("cv", "cover_letter"):
        fname = f"{file_type}{ext}"
    elif file_type == "certificate":
        cert_id = f"cert_{uuid.uuid4().hex[:6]}"
        fname = f"{cert_id}{ext}"
    elif file_type == "video":
        fname = f"video{ext}"
    else:
        att_id = f"doc_{uuid.uuid4().hex[:6]}"
        fname = f"{att_id}{ext}"

    file_path = entity_dir / fname
    file_path.write_bytes(data)

    # Thumbnail for photos
    thumb_url = None
    if file_type == "photo" and ext in (".jpg", ".jpeg", ".png", ".webp"):
        thumb_path = entity_dir / "photo_thumb.jpg"
        if _make_thumbnail(file_path, thumb_path):
            thumb_url = f"/uploads/{dir_name}/{entity_id}/photo_thumb.jpg"

    # Build URL
    rel = file_path.relative_to(_UPLOAD_BASE)
    file_url = f"/uploads/{rel.as_posix()}"

    # Record in Supabase file_uploads table
    try:
        sb = get_svc_client()
        sb.table("file_uploads").insert({
            "entity_type": entity_type,
            "entity_id": entity_id,
            "file_type": file_type,
            "file_url": file_url,
            "file_size": len(data),
        }).execute()

        # Update candidates photo_url/thumb_url if photo upload
        if entity_type == "candidate" and file_type == "photo":
            update_data: dict[str, str] = {"photo_url": file_url}
            if thumb_url:
                update_data["thumb_url"] = thumb_url
            sb.table("candidates").update(update_data).eq("id", entity_id).execute()
    except Exception as e:
        _log_upload.error("File metadata save failed: %s", e)
        # File is saved locally; metadata failure is non-blocking

    return ok(
        data={"file_url": file_url, "thumb_url": thumb_url, "file_size": len(data)},
        message="File uploaded successfully.",
    )


@app.get("/api/admin/files/{entity_type}/{entity_id}", tags=["admin"])
async def admin_list_files(entity_type: str, entity_id: str, request: Request):
    """관리자: 엔티티의 업로드된 파일 목록."""
    _check_admin(request)
    if entity_type not in ("candidate", "inquiry"):
        raise HTTPException(400, "entity_type must be 'candidate' or 'inquiry'")
    try:
        sb = get_svc_client()
        result = (
            sb.table("file_uploads")
            .select("id,file_type,file_url,file_size,created_at")
            .eq("entity_type", entity_type)
            .eq("entity_id", entity_id)
            .eq("is_deleted", False)
            .order("created_at", desc=True)
            .execute()
        )
        return ok(data=result.data or [])
    except Exception as e:
        _log_upload.error("admin_list_files failed: %s", e)
        return ok(data=[])


# ── Audit Log & Security Report ──────────────────────────────────────────────

_AUDIT_DIR = Path(os.getenv("AUDIT_DIR", str(Path(__file__).resolve().parent / "audit")))
_security_warn_store: dict[str, list[float]] = defaultdict(list)

@app.get("/api/admin/audit-log", tags=["admin"])
async def admin_audit_log(request: Request, date: str = "", limit: int = 100):
    """감사 로그 조회 (관리자 전용)."""
    _check_admin(request)
    if limit < 1 or limit > 1000:
        limit = 100
    target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = _AUDIT_DIR / f"audit_{target_date}.jsonl"
    if not log_path.exists():
        return ok(data=[], message=f"No audit log for {target_date}")
    entries = []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except Exception:
        return err("Failed to read audit log", 500)
    return ok(data=entries[-limit:], message=f"{len(entries[-limit:])} entries from {target_date}")


@app.post("/api/security/report", tags=["security"])
async def security_report(request: Request):
    """프론트엔드 보안 이벤트 수신."""
    ip = _ip_hash(request)
    if not _rate_ok(ip, window=60, max_posts=20):
        raise HTTPException(429, "Too many security reports.")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    event_type = str(body.get("type", ""))[:20]
    detail = str(body.get("detail", ""))[:500]
    url = str(body.get("url", ""))[:500]

    if event_type not in ("xss", "sqli", "bot", "devtools", "tampering"):
        raise HTTPException(400, "Invalid event type")

    # Log to security_events.jsonl
    _AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    event_path = _AUDIT_DIR / "security_events.jsonl"
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "ip": ip,
        "type": event_type,
        "detail": detail,
        "url": url,
        "user_agent": (request.headers.get("user-agent") or "")[:200],
    }
    try:
        with open(event_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

    # Track warning threshold: 10+ events in 5 min
    now = time.time()
    _security_warn_store[ip] = [t for t in _security_warn_store[ip] if now - t < 300]
    _security_warn_store[ip].append(now)
    is_warned = len(_security_warn_store[ip]) >= 10

    return ok(message="Event recorded", data={"warned": is_warned})


# ── Admin: Job Status ──────────────────────────────────────────────────────────

class JobStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r'^(open|closed)$')

@app.put("/api/admin/jobs/{job_id}/status", tags=["admin"])
async def admin_update_job_status(job_id: int, body: JobStatusUpdate, request: Request):
    """채용공고 Open/Close 상태 변경 (관리자)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        r = conn.execute("SELECT id FROM jobs WHERE id=? AND is_deleted=0", (job_id,)).fetchone()
        if not r:
            raise HTTPException(404, "Job not found")
        conn.execute("UPDATE jobs SET status=? WHERE id=?", (body.status, job_id))
        conn.commit()
        return ok(message=f"Job #{job_id} status → {body.status}")
    finally:
        conn.close()

@app.put("/api/admin/jobs/{job_id}/hot", tags=["admin"])
async def admin_toggle_job_hot(job_id: int, request: Request):
    """채용공고 HOT 토글 (관리자)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        row = conn.execute("SELECT id, is_hot FROM jobs WHERE id=? AND is_deleted=0", (job_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Job not found")
        new_hot = 0 if row[1] else 1
        conn.execute("UPDATE jobs SET is_hot=? WHERE id=?", (new_hot, job_id))
        conn.commit()
        return ok(message=f"Job #{job_id} hot → {bool(new_hot)}")
    finally:
        conn.close()


# ── Auto Backup Helper ─────────────────────────────────────────────────────────

_db_change_count = 0
_DB_BACKUP_INTERVAL = 10  # 매 10건 변경마다 백업

def _maybe_auto_backup():
    """DB 변경 누적 카운트 → 10건마다 master.db.auto_backup 생성."""
    global _db_change_count
    _db_change_count += 1
    if _db_change_count % _DB_BACKUP_INTERVAL != 0:
        return
    try:
        import shutil
        src = _ADMIN_DB_PATH
        dst = src.with_suffix(".db.auto_backup")
        shutil.copy2(str(src), str(dst))
        logging.getLogger("bridge.api").info("AUTO_BACKUP: master.db → %s (after %d changes)", dst.name, _db_change_count)
    except Exception as e:
        logging.getLogger("bridge.api").warning("AUTO_BACKUP failed: %s", e)


# ── Admin: Create Job from Inquiry ─────────────────────────────────────────────

@app.post("/api/admin/jobs/create-from-inquiry/{inquiry_id}", tags=["admin"])
async def admin_create_job_from_inquiry(inquiry_id: int, request: Request):
    """채용의뢰를 기반으로 새 job 레코드 생성 (PII 분리)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        inq = conn.execute("SELECT * FROM client_inquiries WHERE id = ?", (inquiry_id,)).fetchone()
        if not inq:
            raise HTTPException(404, "Inquiry not found")

        # 재등록 방지: notes에 'JOB_REGISTERED' 마커 확인
        notes = inq["notes"] or ""
        if "JOB_REGISTERED" in notes:
            raise HTTPException(409, "이미 등록된 채용의뢰입니다.")

        # 새 job_code 생성 (max seq + 1)
        max_row = conn.execute("SELECT MAX(id) FROM jobs").fetchone()
        new_id = (max_row[0] or 0) + 1
        job_code = f"Job.{new_id + 1000}"

        # 급여 파싱
        salary_raw = inq["salary_raw"] or ""
        salary_nums = re.findall(r"[\d,.]+", salary_raw.replace(",", ""))
        salary_min = float(salary_nums[0]) if salary_nums else None
        salary_max = float(salary_nums[-1]) if len(salary_nums) > 1 else salary_min

        # 근무시간 → daily_hours 파싱
        wh = inq["working_hours"] or inq["schedule"] or ""
        daily_hours = None
        time_match = re.search(r"(\d{1,2}):?(\d{2})\s*[~\-]\s*(\d{1,2}):?(\d{2})", wh)
        if time_match:
            h1 = int(time_match.group(1)) + int(time_match.group(2)) / 60
            h2 = int(time_match.group(3)) + int(time_match.group(4)) / 60
            daily_hours = round(h2 - h1, 2) if h2 > h1 else None

        # city 추출 (location에서 첫 단어)
        loc = inq["location"] or ""
        city = loc.split(",")[0].split(" ")[0].strip() if loc else ""

        conn.execute(
            """INSERT INTO jobs (job_code, seq, location, city, start_date, teaching_age,
               working_hours, daily_hours, salary_min, salary_max, salary_raw,
               vacation, housing, benefits, status, is_hot, is_deleted, created_at)
               VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', 0, 0, ?)""",
            (
                job_code, loc, city, inq["start_date"], inq["teaching_age"],
                wh, daily_hours, salary_min, salary_max, salary_raw,
                inq["vacation"], inq["housing_detail"] or inq["housing_type"],
                inq["benefits"], datetime.now(timezone.utc).isoformat(),
            ),
        )

        # inquiry에 등록 마커 추가
        new_notes = f"{notes}\nJOB_REGISTERED:{job_code}".strip()
        conn.execute("UPDATE client_inquiries SET notes = ? WHERE id = ?", (new_notes, inquiry_id))
        conn.commit()
        _maybe_auto_backup()
        return ok(message=f"Job {job_code} 생성 완료", data={"job_code": job_code})
    finally:
        conn.close()


# ── Admin: Boards 관리 ─────────────────────────────────────────────────────────

def _ensure_boards_table():
    """boards 테이블 생성 (없으면)."""
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS boards (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            label_kr TEXT,
            display_mode TEXT DEFAULT 'list',
            sort_order INTEGER DEFAULT 0,
            is_hidden INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

_ensure_boards_table()


class BoardCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-z0-9_]+$')
    label: str = Field(..., min_length=1, max_length=100)
    label_kr: Optional[str] = Field(None, max_length=100)
    display_mode: str = Field('list', pattern=r'^(list|card|gallery)$')


class BoardUpdate(BaseModel):
    label: Optional[str] = Field(None, min_length=1, max_length=100)
    label_kr: Optional[str] = Field(None, max_length=100)
    display_mode: Optional[str] = Field(None, pattern=r'^(list|card|gallery)$')
    sort_order: Optional[int] = None
    is_hidden: Optional[int] = Field(None, ge=0, le=1)


@app.get("/api/admin/boards", tags=["admin"])
async def admin_list_boards(request: Request):
    """게시판 목록 (관리자)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM boards ORDER BY sort_order, id"
        ).fetchall()
        return ok(data={"boards": [dict(r) for r in rows]})
    finally:
        conn.close()


@app.post("/api/admin/boards", status_code=201, tags=["admin"])
async def admin_create_board(body: BoardCreate, request: Request):
    """게시판 추가 (관리자)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        existing = conn.execute("SELECT id FROM boards WHERE id=?", (body.id,)).fetchone()
        if existing:
            raise HTTPException(409, f"Board '{body.id}' already exists")
        conn.execute(
            "INSERT INTO boards (id, label, label_kr, display_mode) VALUES (?,?,?,?)",
            (body.id, body.label, body.label_kr, body.display_mode),
        )
        conn.commit()
        return ok(data={"id": body.id}, message="Board created")
    finally:
        conn.close()


@app.put("/api/admin/boards/{board_id}", tags=["admin"])
async def admin_update_board(board_id: str, body: BoardUpdate, request: Request):
    """게시판 설정 변경 (관리자)."""
    _check_admin(request)
    updates: list[str] = []
    params: list = []
    if body.label is not None:
        updates.append("label=?"); params.append(body.label)
    if body.label_kr is not None:
        updates.append("label_kr=?"); params.append(body.label_kr)
    if body.display_mode is not None:
        updates.append("display_mode=?"); params.append(body.display_mode)
    if body.sort_order is not None:
        updates.append("sort_order=?"); params.append(body.sort_order)
    if body.is_hidden is not None:
        updates.append("is_hidden=?"); params.append(body.is_hidden)
    if not updates:
        raise HTTPException(400, "수정할 항목이 없습니다.")
    params.append(board_id)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        r = conn.execute("SELECT id FROM boards WHERE id=?", (board_id,)).fetchone()
        if not r:
            raise HTTPException(404, "Board not found")
        conn.execute(f"UPDATE boards SET {', '.join(updates)} WHERE id=?", params)
        conn.commit()
        return ok(message=f"Board '{board_id}' updated")
    finally:
        conn.close()


@app.delete("/api/admin/boards/{board_id}", tags=["admin"])
async def admin_delete_board(board_id: str, request: Request):
    """게시판 숨김 (soft delete: is_hidden=1)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        r = conn.execute("SELECT id FROM boards WHERE id=?", (board_id,)).fetchone()
        if not r:
            raise HTTPException(404, "Board not found")
        conn.execute("UPDATE boards SET is_hidden=1 WHERE id=?", (board_id,))
        conn.commit()
        return ok(message=f"Board '{board_id}' hidden")
    finally:
        conn.close()


# ── Admin: Banners 관리 ───────────────────────────────────────────────────────

def _ensure_banners_table():
    """banners 테이블 생성 (없으면)."""
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS banners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_url TEXT NOT NULL,
            link_url TEXT,
            position TEXT DEFAULT 'main_top',
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

_ensure_banners_table()


class BannerCreate(BaseModel):
    image_url: str = Field(..., min_length=1, max_length=500)
    link_url: Optional[str] = Field(None, max_length=500)
    position: str = Field('main_top', pattern=r'^(main_top|board_top|sidebar)$')
    is_active: int = Field(1, ge=0, le=1)
    sort_order: int = Field(0)


class BannerUpdate(BaseModel):
    image_url: Optional[str] = Field(None, min_length=1, max_length=500)
    link_url: Optional[str] = Field(None, max_length=500)
    position: Optional[str] = Field(None, pattern=r'^(main_top|board_top|sidebar)$')
    is_active: Optional[int] = Field(None, ge=0, le=1)
    sort_order: Optional[int] = None


@app.get("/api/admin/banners", tags=["admin"])
async def admin_list_banners(request: Request):
    """배너 목록 (관리자)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM banners ORDER BY sort_order, id"
        ).fetchall()
        return ok(data={"banners": [dict(r) for r in rows]})
    finally:
        conn.close()


@app.post("/api/admin/banners", status_code=201, tags=["admin"])
async def admin_create_banner(body: BannerCreate, request: Request):
    """배너 추가 (관리자)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        cur = conn.execute(
            "INSERT INTO banners (image_url, link_url, position, is_active, sort_order) VALUES (?,?,?,?,?)",
            (body.image_url, body.link_url, body.position, body.is_active, body.sort_order),
        )
        new_id = cur.lastrowid
        conn.commit()
        return ok(data={"id": new_id}, message="Banner created")
    finally:
        conn.close()


@app.put("/api/admin/banners/{banner_id}", tags=["admin"])
async def admin_update_banner(banner_id: int, body: BannerUpdate, request: Request):
    """배너 수정 (관리자)."""
    _check_admin(request)
    updates: list[str] = []
    params: list = []
    if body.image_url is not None:
        updates.append("image_url=?"); params.append(body.image_url)
    if body.link_url is not None:
        updates.append("link_url=?"); params.append(body.link_url)
    if body.position is not None:
        updates.append("position=?"); params.append(body.position)
    if body.is_active is not None:
        updates.append("is_active=?"); params.append(body.is_active)
    if body.sort_order is not None:
        updates.append("sort_order=?"); params.append(body.sort_order)
    if not updates:
        raise HTTPException(400, "수정할 항목이 없습니다.")
    params.append(banner_id)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        r = conn.execute("SELECT id FROM banners WHERE id=?", (banner_id,)).fetchone()
        if not r:
            raise HTTPException(404, "Banner not found")
        conn.execute(f"UPDATE banners SET {', '.join(updates)} WHERE id=?", params)
        conn.commit()
        return ok(message=f"Banner #{banner_id} updated")
    finally:
        conn.close()


@app.delete("/api/admin/banners/{banner_id}", tags=["admin"])
async def admin_delete_banner(banner_id: int, request: Request):
    """배너 비활성화 (soft delete: is_active=0)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        r = conn.execute("SELECT id FROM banners WHERE id=?", (banner_id,)).fetchone()
        if not r:
            raise HTTPException(404, "Banner not found")
        conn.execute("UPDATE banners SET is_active=0 WHERE id=?", (banner_id,))
        conn.commit()
        return ok(message=f"Banner #{banner_id} deactivated")
    finally:
        conn.close()


# ── Admin: Posts PUT/DELETE alias ─────────────────────────────────────────────

class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    body:  Optional[str] = Field(None, min_length=10, max_length=10000)
    board: Optional[str] = None


@app.put("/api/admin/posts/{post_id}", tags=["admin"])
async def admin_put_post(post_id: int, body: PostUpdate, request: Request):
    """게시글 수정 — PUT alias (관리자)."""
    _check_admin(request)
    _tag_re = re.compile(r'<[^>]+>')
    updates: list[str] = []
    params: list = []
    if body.title is not None:
        updates.append("title=?"); params.append(_tag_re.sub('', body.title.strip()))
    if body.body is not None:
        updates.append("body=?"); params.append(_tag_re.sub('', body.body.strip()))
    if body.board is not None:
        updates.append("board=?"); params.append(body.board)
    if not updates:
        raise HTTPException(400, "수정할 항목이 없습니다.")
    params.append(post_id)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        r = conn.execute(
            "SELECT id FROM community_posts WHERE id=? AND is_deleted=0", (post_id,)
        ).fetchone()
        if not r:
            raise HTTPException(404, "Post not found")
        conn.execute(f"UPDATE community_posts SET {', '.join(updates)} WHERE id=?", params)
        conn.commit()
        return ok(message=f"Post #{post_id} updated")
    finally:
        conn.close()


@app.delete("/api/admin/posts/{post_id}", tags=["admin"])
async def admin_delete_post(post_id: int, request: Request):
    """게시글 삭제 — soft delete (관리자, 게시판 무관)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        r = conn.execute(
            "SELECT id FROM community_posts WHERE id=? AND is_deleted=0", (post_id,)
        ).fetchone()
        if not r:
            raise HTTPException(404, "Post not found")
        conn.execute("UPDATE community_posts SET is_deleted=1 WHERE id=?", (post_id,))
        conn.commit()
        return ok(message=f"Post #{post_id} deleted")
    finally:
        conn.close()


# ── 통합 수신함 + Gmail 라우터 등록 ──────────────────────────────────────────
from inbox_api import router as inbox_router
from gmail_collector import router as gmail_router
app.include_router(inbox_router)
app.include_router(gmail_router)

# ── Static Files Mount (개발 환경용) ──────────────────────────────────────────
if not _IS_PROD:
    app.mount("/uploads", StaticFiles(directory=str(_UPLOAD_BASE)), name="uploads")


# ── 로컬 실행 ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("BRIDGE API Server 시작 중...")
    print("  문서: http://localhost:8000/docs")
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)

