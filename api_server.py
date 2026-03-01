"""
BRIDGE API Server — FastAPI 초안
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
import uuid
import sqlite3
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Any
import hashlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── dotenv ──────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

# ── FastAPI / Supabase 임포트 ────────────────────────────────────────────────
try:
    from fastapi import FastAPI, HTTPException, Request, status, UploadFile, File as FastFile
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
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        ct = response.headers.get("content-type", "")
        if "application/json" not in ct:
            return response

        # 관리자 인증된 /api/admin/ 요청은 PII 마스킹 통과 (원본 데이터 반환)
        _ak = os.getenv("ADMIN_API_KEY", "")
        if (request.url.path.startswith("/api/admin/")
                and _ak
                and request.headers.get("x-admin-key", "") == _ak):
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

# CORS 허용 출처
ALLOWED_ORIGINS = [
    "https://bridgejob.co.kr",
    "https://www.bridgejob.co.kr",
    "http://localhost:3000",   # 개발용
    "http://localhost:3001",   # 개발용
    "http://localhost:3002",   # 개발용
    "http://localhost:8080",   # 개발용
]

# ── 앱 초기화 ─────────────────────────────────────────────────────────────────
# 프로덕션에서는 API 문서 비활성화 (BRIDGE_ENV=production 설정 시)
_IS_PROD = os.getenv("BRIDGE_ENV", "").lower() in ("production", "prod")

app = FastAPI(
    title="BRIDGE Recruitment API",
    description="bridgejob.co.kr 웹사이트 백엔드",
    version="1.0.0",
    docs_url=None if _IS_PROD else "/docs",
    redoc_url=None if _IS_PROD else "/redoc",
)

# PII 마스킹 미들웨어 — CORS보다 먼저 등록해야 응답 전체를 커버
app.add_middleware(PIIMaskingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Admin-Key"],
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


@app.get("/api/jobs", tags=["jobs"])
async def list_jobs(
    request:   Request,
    city:      Optional[str] = None,
    is_hot:    Optional[bool] = None,
    limit:     int = 50,
    offset:    int = 0,
):
    """
    공개 구인 목록 조회 (status='open' 만 반환, RLS 적용)
    - city: 도시 필터 (서울, 인천, 수원 등)
    - is_hot: HOT 포지션만 (true/false)
    - limit / offset: 페이지네이션
    """
    if not _rate_ok(_ip_hash(request), window=60, max_posts=60):
        raise HTTPException(429, "Too many requests. Please slow down.")
    try:
        sb = get_anon_client()
        query = (
            sb.table("jobs")
            .select(
                "id,job_code,seq,city,district,location,"
                "start_date,teaching_age,working_hours,"
                "salary_min,salary_max,salary_raw,"
                "housing,benefits,vacation,"
                "is_hot,is_part_time,status"
            )
            .eq("status", "open")
            .order("is_hot", desc=True)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if city:
            city = city.strip()[:50]
            query = query.ilike("city", f"%{city}%")
        if is_hot is not None:
            query = query.eq("is_hot", is_hot)

        result = query.execute()
        return ok(data=result.data, message=f"{len(result.data)}건 조회")

    except Exception as e:
        import logging as _log_jobs
        _log_jobs.getLogger("bridge.api").error("list_jobs 실패: %s", e, exc_info=True)
        err("구인 목록을 불러올 수 없습니다. 잠시 후 다시 시도해주세요.", 500)


# 공개 job 상세 조회에서 반환할 안전한 컬럼 목록
# school_name, contact_name, phone, email, employer_id 등 민감 필드 명시적 제외
_SAFE_JOB_FIELDS = (
    "id,job_code,seq,city,district,location,"
    "employment_type,start_date,teaching_age_groups,"
    "class_size,working_hours,hours_per_day,hours_per_week,"
    "salary_min,salary_max,salary_raw,"
    "housing_provided,housing_detail,"
    "vacation_days,visa_sponsorship,"
    "benefits,native_count,"
    "is_hot,status,published_at"
)


@app.get("/api/jobs/{job_id}", tags=["jobs"])
async def get_job(job_id: str, request: Request):
    """포지션 상세 조회 — 민감 필드(구인처 연락처/주소 등) 제외"""
    if not _rate_ok(_ip_hash(request), window=60, max_posts=60):
        raise HTTPException(429, "Too many requests. Please slow down.")
    try:
        sb = get_anon_client()
        result = (
            sb.table("jobs")
            .select(_SAFE_JOB_FIELDS)   # select("*") 대신 명시적 안전 컬럼만
            .eq("id", job_id)
            .eq("status", "open")
            .single()
            .execute()
        )
        if not result.data:
            err("포지션을 찾을 수 없습니다.", 404)
        return ok(data=result.data)

    except HTTPException:
        raise
    except Exception as e:
        import logging as _log_job
        _log_job.getLogger("bridge.api").error("get_job 실패: %s", e, exc_info=True)
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
        sb = get_svc_client()
        now_iso = datetime.now(timezone.utc).isoformat()

        payload = body.model_dump(exclude_none=True)
        token_in = payload.pop("apply_token", None)   # 모델에서 제거 후 별도 처리

        # PII 암호화
        for field in _CANDIDATE_ENCRYPT:
            if field in payload and payload[field]:
                payload[field] = _encrypt_if_needed(str(payload[field]))

        # dedup key
        dk = _dedup_key(body.full_name, body.dob, body.nationality)
        payload["dedup_key"] = dk
        payload["updated_at"] = now_iso

        existing_id: Optional[str] = None

        # ── 경로 A: JWT 토큰으로 기존 레코드 찾기 ───────────────────────────
        if token_in:
            cid = _verify_candidate_token(token_in)
            if cid:
                existing_id = cid

        # ── 경로 B: 복합 키로 기존 레코드 탐색 (토큰 없거나 검증 실패) ───────
        if not existing_id:
            res = (
                sb.table("candidates")
                .select("id")
                .eq("dedup_key", dk)
                .eq("is_deleted", False)
                .limit(1)
                .execute()
            )
            if res.data:
                existing_id = res.data[0]["id"]

        # ── UPDATE (2차 누적) ───────────────────────────────────────────────
        if existing_id:
            # None 값은 이미 제외(exclude_none)됐으므로 기존 값 덮어쓰지 않음
            sb.table("candidates").update(payload).eq("id", existing_id).execute()
            # 기존 토큰 반환 (없으면 새로 발급)
            tok = _make_candidate_token(existing_id)
            return ok(
                data={"id": existing_id, "apply_token": tok, "mode": "updated"},
                message="지원 정보가 업데이트되었습니다."
            )

        # ── INSERT (1차 신규) ────────────────────────────────────────────────
        payload["source"]     = payload.get("source") or "web_form"
        payload["status"]     = "Active"
        payload["is_deleted"] = False
        payload["created_at"] = now_iso

        result = sb.table("candidates").insert(payload).execute()
        if not result.data:
            err("저장 실패. 잠시 후 다시 시도하세요.", 500)

        new_id = result.data[0].get("id")
        token_out = _make_candidate_token(str(new_id))

        # 확인 이메일 발송 (실패해도 접수는 완료)
        if _EMAIL_OK and body.email:
            send_applicant_confirmation(body.email, body.full_name)

        return ok(
            data={"id": new_id, "apply_token": token_out, "mode": "created"},
            message="지원이 접수되었습니다. 담당자가 검토 후 연락드리겠습니다."
        )

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
        sb = get_svc_client()

        payload = body.model_dump(exclude_none=True)
        # 연락처 PII 암호화 (storage 전 마지막 레이어)
        for field in _INQUIRY_ENCRYPT:
            if field in payload and payload[field]:
                payload[field] = _encrypt_if_needed(str(payload[field]))

        payload["source"]       = "web_form"
        payload["status"]       = "pending"
        payload["submitted_at"] = datetime.now(timezone.utc).isoformat()
        payload["created_at"]   = datetime.now(timezone.utc).isoformat()
        payload["updated_at"]   = datetime.now(timezone.utc).isoformat()

        result = sb.table("client_inquiries").insert(payload).execute()

        if not result.data:
            err("저장 실패. 잠시 후 다시 시도하세요.", 500)

        # 확인 이메일 발송 (실패해도 접수는 완료)
        if _EMAIL_OK and body.email:
            send_employer_confirmation(body.email, body.school_name, body.contact_name or "")

        return ok(
            data={"id": result.data[0].get("id")},
            message="문의가 접수되었습니다. 빠른 시일 내에 연락드리겠습니다."
        )

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
_ADMIN_DB_PATH = Path(os.getenv("BRIDGE_DB_PATH", str(Path(__file__).resolve().parent / "master.db")))
_ADMIN_KEY     = os.getenv("ADMIN_API_KEY", "")

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

    # ── Supabase 통계 (candidates, jobs, payments) ─────────────────────────
    try:
        sb = get_svc_client()
        # 지원자 수
        cands = sb.table("candidates").select("id", count="exact").eq(
            "is_deleted", False
        ).execute()
        stats["candidates"] = cands.count if cands.count is not None else len(cands.data or [])

        # 대기 중 (pending/Active)
        pending = sb.table("candidates").select("id", count="exact").eq(
            "is_deleted", False
        ).eq("status", "Active").execute()
        stats["candidates_active"] = pending.count if pending.count is not None else len(pending.data or [])

        # 결제 통계
        try:
            pays = sb.table("payments").select("id,amount,status").execute()
            pay_data = pays.data or []
            stats["payments_total"] = len(pay_data)
            stats["payments_confirmed"] = sum(1 for p in pay_data if p.get("status") == "confirmed")
            stats["revenue"] = sum(p.get("amount", 0) or 0 for p in pay_data if p.get("status") == "confirmed")
        except Exception:
            stats["payments_total"] = 0
            stats["payments_confirmed"] = 0
            stats["revenue"] = 0

    except Exception:
        stats.setdefault("candidates", 0)
        stats.setdefault("candidates_active", 0)
        stats.setdefault("payments_total", 0)
        stats.setdefault("revenue", 0)

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


@app.get("/api/admin/candidates", tags=["admin"])
async def admin_candidates(
    request:     Request,
    search:      Optional[str] = None,
    nationality: Optional[str] = None,
    visa:        Optional[str] = None,
    limit:       int = 500,
    offset:      int = 0,
):
    """
    지원자 전체 목록 (관리자용 — PII 복호화 포함)
    보호: X-Admin-Key 필수
    """
    _check_admin(request)
    try:
        sb = get_svc_client()
        query = (
            sb.table("candidates")
            .select(
                "id,full_name,email,nationality,ancestry,dob,gender,"
                "current_location,e_visa,mobile_phone,kakaotalk,"
                "certification,employment,area_prefs,target_age,"
                "housing,reference,criminal_record,passport,"
                "photo_url,thumb_url,"
                "admin_notes,status,is_deleted,dedup_key,created_at,updated_at"
            )
            .eq("is_deleted", False)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if search:
            query = query.ilike("full_name", f"%{search}%")
        if nationality:
            query = query.eq("nationality", nationality)
        if visa:
            query = query.ilike("e_visa", f"%{visa}%")

        result = query.execute()
        rows = [_decrypt_row(dict(r)) for r in result.data]

        total_res = (
            sb.table("candidates")
            .select("id", count="exact")
            .eq("is_deleted", False)
            .execute()
        )
        return ok(
            data={"total": total_res.count or len(rows), "candidates": rows},
            message=f"{len(rows)}명 조회",
        )
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
    """인라인 편집: admin_notes, reference, status만 허용 (PII 아님)."""
    _check_admin(request)
    EDITABLE = {"admin_notes", "reference", "status"}
    update = {k: v for k, v in body.items() if k in EDITABLE}
    if not update:
        raise HTTPException(400, "수정 가능한 필드 없음 (admin_notes, reference, status)")
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        sb = get_svc_client()
        res = (
            sb.table("candidates")
            .update(update)
            .eq("id", candidate_id)
            .eq("is_deleted", False)
            .execute()
        )
        return ok(data=res.data[0] if res.data else None, message="수정 완료")
    except Exception as e:
        import logging as _log_upd
        _log_upd.getLogger("bridge.api").error("admin_update 실패: %s", e, exc_info=True)
        err("수정에 실패했습니다.", 500)


@app.delete("/api/admin/candidates/{candidate_id}", tags=["admin"])
async def admin_delete_candidate(candidate_id: str, request: Request):
    """Soft Delete — is_deleted=True 로 설정 (물리 삭제 금지)."""
    _check_admin(request)
    try:
        sb = get_svc_client()
        res = (
            sb.table("candidates")
            .update({"is_deleted": True, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", candidate_id)
            .execute()
        )
        return ok(message="삭제 처리 완료 (soft delete)")
    except Exception as e:
        import logging as _log_del
        _log_del.getLogger("bridge.api").error("admin_delete 실패: %s", e, exc_info=True)
        err("삭제에 실패했습니다.", 500)


# ── Community Board API ──────────────────────────────────────────────────────
_BOARDS = {"visa", "support_kr", "support", "about", "korea", "tips", "testimonials"}
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
    """구직자 + 구인자 접수 통합 목록."""
    _check_admin(request)
    try:
        sb = get_svc_client()
        apps: list[dict] = []

        # 구직자 (candidates)
        cands = sb.table("candidates").select(
            "id,full_name,email,status,created_at,updated_at,is_deleted"
        ).eq("is_deleted", False).order("created_at", desc=True).limit(200).execute()
        for c in (cands.data or []):
            apps.append({
                "id": c["id"], "type": "candidate",
                "name": c.get("full_name") or "", "email": c.get("email") or "",
                "status": c.get("status") or "Active",
                "created_at": c.get("created_at") or "",
                "updated_at": c.get("updated_at"),
            })

        # 구인자 (client_inquiries)
        inqs = sb.table("client_inquiries").select(
            "id,school_name,contact_name,email,status,created_at,updated_at"
        ).order("created_at", desc=True).limit(200).execute()
        for i in (inqs.data or []):
            apps.append({
                "id": i["id"], "type": "employer",
                "name": i.get("contact_name") or "", "email": i.get("email") or "",
                "school_name": i.get("school_name") or "",
                "status": i.get("status") or "pending",
                "created_at": i.get("created_at") or "",
                "updated_at": i.get("updated_at"),
            })

        apps.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return ok(data=apps)

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
    """접수 상태 변경."""
    _check_admin(request)
    try:
        sb = get_svc_client()
        now_iso = datetime.now(timezone.utc).isoformat()
        table = "candidates" if body.type == "candidate" else "client_inquiries"
        sb.table(table).update({
            "status": body.status, "updated_at": now_iso
        }).eq("id", app_id).execute()
        return ok(message=f"{app_id} → {body.status}")

    except HTTPException:
        raise
    except Exception as e:
        import logging as _log_upd
        _log_upd.getLogger("bridge.api").error("admin_update_app 실패: %s", e, exc_info=True)
        err("상태 변경에 실패했습니다.", 500)


# ── Admin: Payments 관리 ──────────────────────────────────────────────────────

@app.get("/api/admin/payments", tags=["admin"])
async def admin_list_payments(request: Request):
    """결제 기록 목록."""
    _check_admin(request)
    try:
        sb = get_svc_client()
        result = sb.table("payments").select("*").order(
            "created_at", desc=True
        ).limit(200).execute()
        return ok(data=result.data or [])

    except HTTPException:
        raise
    except Exception as e:
        import logging as _log_pay
        _log_pay.getLogger("bridge.api").error("admin_payments 실패: %s", e, exc_info=True)
        # payments 테이블이 없을 수 있음 — 빈 배열 반환
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


# ── 통합 수신함 + Gmail 라우터 등록 ─────────────────────────────────────────────
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
