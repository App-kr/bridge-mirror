"""
BRIDGE API Server  v2.2
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
import hmac
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

# ── SafeJSONResponse: 모든 admin 응답에 사용 ────────────────────────────────

class SafeJSONResponse(Response):
    """JSON 직렬화 시 브라우저 JSON.parse 호환성을 100% 보장하는 Response."""
    media_type = "application/json"

    def __init__(self, content=None, status_code=200, headers=None, **kwargs):
        body = json.dumps(
            self._deep_sanitize(content),
            ensure_ascii=False,
            default=str,
        )
        super().__init__(content=body, status_code=status_code, media_type=self.media_type, headers=headers)

    @classmethod
    def _deep_sanitize(cls, obj):
        if isinstance(obj, str):
            obj = obj.replace('\x00', '')
            obj = ''.join(c for c in obj if ord(c) >= 32 or c in '\n\r\t')
            obj = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', obj)
            return obj
        elif isinstance(obj, dict):
            return {cls._deep_sanitize(k): cls._deep_sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [cls._deep_sanitize(v) for v in obj]
        elif isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
        return obj

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

# ── security 패키지 (PIIScanner + InputSanitizer만 사용) ─────────────────
# 암호화: security_vault.py (위에서 import 완료)
# PII 스캔 + 입력 검증: security/ 패키지
try:
    from security import PIIScanner, InputSanitizer
    _sec_scanner = PIIScanner(fail_closed=True)
    _sec_sanitizer = InputSanitizer()
    _SECURITY_PKG_OK = True
except Exception as _sec_exc:
    _SECURITY_PKG_OK = False
    _sec_scanner = None
    _sec_sanitizer = None
    print(f"[WARN] security 패키지 로드 실패 (선택적): {_sec_exc}")

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
            clean_body = json.dumps(clean, ensure_ascii=False, default=str).encode("utf-8")
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
    default_response_class=SafeJSONResponse,
)

# 보안 미들웨어 — 헤더 + Rate Limit + 감사 로그
try:
    from security_middleware import SecurityMiddleware, security_router, admin_security_router
    app.add_middleware(SecurityMiddleware)
    app.include_router(security_router)
    app.include_router(admin_security_router)
except ImportError:
    pass  # 선택적: 파일 없으면 무시

# PII 마스킹 미들웨어 — CORS보다 먼저 등록해야 응답 전체를 커버
app.add_middleware(PIIMaskingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Admin-Key", "X-Admin-Token", "X-Bridge-Signature"],
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

    # ── 수업 대상 & 서류 ─────────────────────────────────────────────────────
    target:                  Optional[str] = None   # Target (Kindy, Elem 등)
    target_age:              Optional[str] = None   # Preferred age group
    korean_criminal_record:  Optional[str] = None   # 한국 내 범죄기록
    documents:               Optional[str] = None   # 서류 준비 상태

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
    return {"success": True, "message": message, "data": _sanitize_data(data)}


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

# ── CandidateApply 모델 → DB 컬럼 매핑 ───────────────────────────────────────
_APPLY_FIELD_MAP = {
    "education":                "education_level",
    "marital_status":           "married",
    "personal_considerations":  "personal_consideration",
    "agreement":                "consent",
    "facts":                    "fact_check",
    "admin_notes":              "notes",
}

# payload에서 제거할 키 (DB 컬럼으로 직접 INSERT 불가)
_APPLY_SKIP_FIELDS = {"file_urls", "apply_token"}


def _map_apply_payload(payload: dict) -> dict:
    """CandidateApply 모델 필드명 → candidates DB 컬럼명 변환"""
    mapped = {}
    for k, v in payload.items():
        if k in _APPLY_SKIP_FIELDS:
            continue
        db_key = _APPLY_FIELD_MAP.get(k, k)
        mapped[db_key] = v
    mapped["source_file"] = "web_form"
    return mapped


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
    # Input Sanitizer 검증
    if _SECURITY_PKG_OK and _sec_sanitizer:
        for _f in ["full_name", "email", "phone", "message"]:
            _v = getattr(body, _f, None)
            if _v and isinstance(_v, str) and not _sec_sanitizer.is_safe(_v):
                raise HTTPException(400, "유효하지 않은 입력입니다.")
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
                db_payload = _map_apply_payload(payload)
                sets = ", ".join(f"{k} = ?" for k in db_payload if k != "candidate_id")
                vals = [v for k, v in db_payload.items() if k != "candidate_id"]
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

            db_payload = _map_apply_payload(payload)
            cols = ", ".join(db_payload.keys())
            placeholders = ", ".join("?" * len(db_payload))
            conn.execute(
                f"INSERT INTO candidates ({cols}) VALUES ({placeholders})",
                list(db_payload.values()),
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
    # Input Sanitizer 검증
    if _SECURITY_PKG_OK and _sec_sanitizer:
        for _f in ["school_name", "contact_name", "email", "phone", "message"]:
            _v = getattr(body, _f, None)
            if _v and isinstance(_v, str) and not _sec_sanitizer.is_safe(_v):
                raise HTTPException(400, "유효하지 않은 입력입니다.")
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
    return SafeJSONResponse(
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


def _ensure_access_logs():
    """access_logs 테이블 생성 (없으면)"""
    try:
        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("CREATE TABLE IF NOT EXISTS access_logs (id INTEGER PRIMARY KEY, ip TEXT, url TEXT, timestamp TEXT DEFAULT (datetime('now')))")
        conn.commit()
        conn.close()
    except Exception:
        pass

_ensure_access_logs()


def _log_unauthorized_access(request: Request):
    """비관리자 접근 시 IP + URL + 시간 기록"""
    try:
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown").split(",")[0].strip()
        url = str(request.url.path)
        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("INSERT INTO access_logs (ip, url) VALUES (?, ?)", (ip, url))
        conn.commit()
        conn.close()
    except Exception:
        pass


def _verify_admin_password(input_pw: str, stored: str) -> bool:
    """평문 또는 pbkdf2 해시 비교 (하위 호환)"""
    if stored.startswith("pbkdf2:sha256:"):
        try:
            _, _, iterations, salt, dk_hex = stored.split(":", 4)
            dk = hashlib.pbkdf2_hmac("sha256", input_pw.encode(), salt.encode(), int(iterations))
            return hmac.compare_digest(dk.hex(), dk_hex)
        except Exception:
            return False
    # 기존 평문 비교 (마이그레이션 전 호환)
    return hmac.compare_digest(input_pw, stored)


def _check_admin(request: Request):
    """ADMIN_API_KEY 헤더 검증. 프로덕션에서 키 미설정 시 접근 차단."""
    if not _ADMIN_KEY:
        if _IS_PROD:
            raise HTTPException(status_code=503, detail="관리자 기능이 비활성화되어 있습니다.")
        # 개발 환경에서만 키 없이 통과 허용
        return
    if request.headers.get("x-admin-key", "").strip() != _ADMIN_KEY.strip():
        _log_unauthorized_access(request)
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
    if not _verify_admin_password(pw, _ADMIN_PW):
        raise HTTPException(403, "비밀번호가 올바르지 않습니다.")
    # 로그인 성공 → 해당 IP 블랙리스트 자동 리셋
    try:
        from security_middleware import ip_blacklist, SecurityMiddleware
        real_ip = SecurityMiddleware._get_real_ip(request)
        if real_ip in ip_blacklist._list:
            del ip_blacklist._list[real_ip]
            ip_blacklist._save()
    except Exception:
        pass
    return ok(data={"api_key": _ADMIN_KEY}, message="로그인 성공")


@app.post("/api/admin/change-password", tags=["admin"])
async def admin_change_password(request: Request):
    """관리자 비밀번호 변경 — PBKDF2 해시로 .env 업데이트."""
    _check_admin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")
    new_pw = str(body.get("new_password", "")).strip()
    if len(new_pw) < 8:
        raise HTTPException(400, "비밀번호는 8자 이상이어야 합니다.")
    import secrets as _sec
    import re as _re
    salt = _sec.token_hex(16)
    iterations = 260000
    dk = hashlib.pbkdf2_hmac("sha256", new_pw.encode(), salt.encode(), iterations)
    new_hash = f"pbkdf2:sha256:{iterations}:{salt}:{dk.hex()}"
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        updated = _re.sub(r"^ADMIN_PASSWORD=.*$", f"ADMIN_PASSWORD={new_hash}",
                          content, flags=_re.MULTILINE)
        env_path.write_text(updated, encoding="utf-8")
    global _ADMIN_PW
    _ADMIN_PW = new_hash
    return ok(data={"hash": new_hash}, message="비밀번호 변경 완료. 서버 재시작 후 완전 적용됩니다.")


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

        try:
            r = conn2.execute("SELECT COUNT(*) AS n FROM payments").fetchone()
            stats["payments_total"] = r["n"] if r else 0
            r = conn2.execute("SELECT COUNT(*) AS n FROM payments WHERE status='confirmed'").fetchone()
            stats["payments_confirmed"] = r["n"] if r else 0
            r = conn2.execute("SELECT COALESCE(SUM(amount),0) AS n FROM payments WHERE status='confirmed'").fetchone()
            stats["revenue"] = r["n"] if r else 0
        except Exception:
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
    """Remove all characters that can break JSON parsing in any browser/runtime."""
    if not isinstance(v, str):
        return v
    # 1. Null bytes
    v = v.replace('\x00', '')
    # 2. All C0 control chars except \t \n \r (which json.dumps handles)
    v = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', v)
    # 3. C1 control chars (U+0080–U+009F) — break some parsers
    v = re.sub(r'[\x80-\x9f]', '', v)
    # 4. Unicode surrogates (U+D800–U+DFFF) — invalid in JSON
    v = re.sub(r'[\ud800-\udfff]', '', v)
    # 5. BOM and other zero-width chars
    v = v.replace('\ufeff', '').replace('\ufffe', '')
    return v


def _sanitize_data(obj):
    """Recursively sanitize all string values in nested dicts/lists."""
    if isinstance(obj, str):
        return _sanitize_str(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_data(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_data(item) for item in obj]
    return obj


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

            payload = ok(
                data={"total": total, "candidates": candidates},
                message=f"{len(candidates)}명 조회",
            )
            return SafeJSONResponse(content=payload)
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logging.getLogger("bridge.api").error("admin_candidates 조회 실패: %s", e, exc_info=True)
        err("지원자 목록을 불러올 수 없습니다.", 500)


@app.post("/api/admin/candidates", tags=["admin"])
async def admin_create_candidate(request: Request, body: dict):
    """새 후보자 추가 (관리자 전용)."""
    _check_admin(request)
    if not _rate_ok(request):
        raise HTTPException(429, "잠시 후 다시 시도해주세요.")
    full_name = (body.get("full_name") or "").strip()
    if not full_name:
        raise HTTPException(400, "이름(full_name)은 필수입니다.")
    import uuid as _uuid_cand
    cid = f"cnd_{_uuid_cand.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    ALLOWED = {
        "email", "full_name", "nationality", "ancestry", "dob", "gender",
        "current_location", "education_level", "major", "certification",
        "e_visa", "arc_holders", "passport", "criminal_record", "documents",
        "start_date", "target", "area_prefs", "job_prefs", "experience",
        "employment", "reference", "current_salary", "desired_salary",
        "interview_time", "housing", "personal_consideration", "religion",
        "health_info", "piercings", "dependents", "pets", "married",
        "korean_criminal_record", "kakaotalk", "mobile_phone", "consent",
        "fact_check", "notes", "status", "source", "tattoo", "visa_type",
        "working_hours", "target_age",
    }
    record = {k: v for k, v in body.items() if k in ALLOWED and v}
    record["candidate_id"] = cid
    record["created_at"] = now
    record["updated_at"] = now
    record["source"] = record.get("source", "admin_manual")
    record["source_file"] = "admin_manual"
    record["status"] = record.get("status", "Active")
    cols = ", ".join(record.keys())
    placeholders = ", ".join("?" for _ in record)
    try:
        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            conn.execute(
                f"INSERT INTO candidates ({cols}) VALUES ({placeholders})",
                list(record.values()),
            )
            conn.commit()
            return ok(data={"candidate_id": cid}, message="후보자 등록 완료")
        finally:
            conn.close()
    except Exception as e:
        logging.getLogger("bridge.api").error("admin_create_candidate 실패: %s", e, exc_info=True)
        err("후보자 등록에 실패했습니다.", 500)


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
        "interview_time", "job_prefs", "invoice", "tattoo", "visa_type",
        "working_hours", "photo_url", "thumb_url",
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
async def admin_list_inquiries(
    request: Request,
    limit: int = 1000,
    offset: int = 0,
    q: str = "",
    source: str = "",
):
    """채용의뢰 목록 — client_inquiries 테이블. q=검색어, source=소스필터."""
    _check_admin(request)
    try:
        conn = sqlite3.connect(str(_ADMIN_DB_PATH))
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.row_factory = sqlite3.Row
        try:
            where_clauses = []
            params: list = []
            if q:
                where_clauses.append(
                    "(school_name LIKE ? OR contact_name LIKE ? OR email LIKE ? OR phone LIKE ? OR memo LIKE ? OR location LIKE ?)"
                )
                like = f"%{q}%"
                params.extend([like] * 6)
            if source:
                where_clauses.append("source_file = ?")
                params.append(source)
            where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
            total = conn.execute(f"SELECT COUNT(*) FROM client_inquiries{where_sql}", params).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM client_inquiries{where_sql} ORDER BY id DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
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
_SMTP_USER = os.getenv("BRIDGE_SMTP_USER", os.getenv("SMTP_USER", os.getenv("GMAIL_USER", "")))
_SMTP_PASS = os.getenv("BRIDGE_SMTP_PASS", os.getenv("SMTP_PASS", os.getenv("GMAIL_APP_PASSWORD", "")))
_log_email = logging.getLogger("bridge.email_send")

# template_key → candidates 컬럼 매핑
_TEMPLATE_COL_MAP = {
    "contract_offer":       "email_contract",
    "immigration_guide":    "email_immigration",
    "overseas_visa_prep":   "email_overseas",
    "job_transition_guide": "email_transition",
    "arrival_guide":        "email_arrival",
}


# ── SECURITY: PII 스캔 — 메일 본문에 개인정보 포함 시 발송 차단 ───────────────
_PII_EMAIL_RE = re.compile(r'[\w.\-+]+@[\w.\-]+\.\w+')
_PII_PHONE_RE = re.compile(r'\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{4}')
_PII_KR_ID_RE = re.compile(r'\d{6}-[1-4]\d{6}')

# 허용 이메일: BRIDGE 공식 이메일은 PII 스캔에서 제외
_SAFE_EMAILS = frozenset({"bridgejobkr@gmail.com", "bridgejobkr@naver.com"})


def _pii_scan_body(html_body: str) -> list[str]:
    """메일 본문에서 PII 패턴 감지. 위반 항목 리스트 반환 (빈 리스트 = 안전)."""
    violations: list[str] = []
    # SECURITY: 이메일 주소 패턴 감지
    found_emails = _PII_EMAIL_RE.findall(html_body)
    unsafe_emails = [e for e in found_emails if e.lower() not in _SAFE_EMAILS]
    if unsafe_emails:
        violations.append(f"이메일 주소 감지: {len(unsafe_emails)}건")
    # SECURITY: 전화번호 패턴 감지
    if _PII_PHONE_RE.search(html_body):
        violations.append("전화번호 패턴 감지")
    # SECURITY: 주민등록번호 패턴 감지
    if _PII_KR_ID_RE.search(html_body):
        violations.append("주민등록번호 패턴 감지")
    return violations


# ── SECURITY: 메일 발송 Rate Limiter (3초 간격, 10/분, 200/일) ──────────────
_MAIL_SEND_TIMES: list[float] = []
_MAIL_DAILY_COUNT: dict[str, int] = {}  # date_str → count
_MAIL_RATE_LOCK = threading.Lock()


def _mail_rate_check() -> tuple[bool, str]:
    """메일 발송 속도 제한 체크. (통과여부, 거부사유)."""
    now = _time.time()
    today = datetime.now().strftime("%Y-%m-%d")

    with _MAIL_RATE_LOCK:
        # SECURITY: 일일 최대 200통
        daily = _MAIL_DAILY_COUNT.get(today, 0)
        if daily >= 200:
            return False, "일일 발송 한도 초과 (200통/일)"

        # SECURITY: 분당 최대 10통
        recent_min = [t for t in _MAIL_SEND_TIMES if now - t < 60]
        if len(recent_min) >= 10:
            return False, "분당 발송 한도 초과 (10통/분)"

        # SECURITY: 최소 3초 간격
        if _MAIL_SEND_TIMES and (now - _MAIL_SEND_TIMES[-1]) < 3:
            return False, "발송 간격 부족 (최소 3초)"

        return True, ""


def _mail_rate_record():
    """발송 성공 시 카운트 기록."""
    now = _time.time()
    today = datetime.now().strftime("%Y-%m-%d")
    with _MAIL_RATE_LOCK:
        _MAIL_SEND_TIMES.append(now)
        # 5분 이상 된 타임스탬프 정리
        cutoff = now - 300
        while _MAIL_SEND_TIMES and _MAIL_SEND_TIMES[0] < cutoff:
            _MAIL_SEND_TIMES.pop(0)
        _MAIL_DAILY_COUNT[today] = _MAIL_DAILY_COUNT.get(today, 0) + 1
        # 어제 이전 카운트 정리
        for d in list(_MAIL_DAILY_COUNT.keys()):
            if d != today:
                del _MAIL_DAILY_COUNT[d]


def _smtp_send(to_email: str, subject: str, html_body: str, reply_to: str = "bridgejobkr@gmail.com") -> bool:
    """Gmail SMTP로 이메일 발송. 실패 시 False."""
    if not _SMTP_USER or not _SMTP_PASS or _SMTP_PASS == "your_app_password":
        _log_email.warning("SMTP 미설정 — 발송 스킵 (to=%s)", to_email)
        return False
    try:
        msg = MIMEMultipart("alternative")
        # SECURITY: From 고정 — BRIDGE 공식 계정
        msg["From"] = f"BRIDGE <{_SMTP_USER}>"
        # SECURITY: To에 수신자 1명만 — CC/BCC 절대 금지
        msg["To"] = to_email
        msg["Subject"] = subject
        # SECURITY: Reply-To → 우리 메일로만 회신
        msg["Reply-To"] = reply_to
        # SECURITY: X-Mailer 헤더 미설정 (기본 제거)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        ctx = _ssl.create_default_context()
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as srv:
            srv.ehlo()
            srv.starttls(context=ctx)
            srv.ehlo()
            srv.login(_SMTP_USER, _SMTP_PASS)
            # SECURITY: sendmail에 수신자 1명만 전달
            srv.sendmail(_SMTP_USER, [to_email], msg.as_string())

        _log_email.info("이메일 발송 성공: %s → %s", subject[:40], to_email)
        return True
    except Exception as e:
        _log_email.error("이메일 발송 실패 (to=%s): %s", to_email, e, exc_info=True)
        return False


def _secure_send_email(to_email: str, subject: str, html_body: str,
                       skip_pii_scan: bool = False) -> tuple[bool, str]:
    """보안 규칙 적용 이메일 발송. (성공여부, 메시지) 반환.

    Security rules applied:
    1. 개별 발송 (CC/BCC 없음) — _smtp_send에서 강제
    2. PII 스캔 — 본문에 개인정보 감지 시 차단
    3. Rate limit — 3초 간격, 10/분, 200/일
    4. Reply-To 격리 — bridgejobkr@gmail.com
    """
    # SECURITY: PII 스캔
    if not skip_pii_scan:
        violations = _pii_scan_body(html_body)
        if violations:
            detail = "; ".join(violations)
            _log_email.warning("PII 발송 차단 (to=%s): %s", to_email, detail)
            return False, f"PII 위반으로 발송 차단: {detail}"

    # SECURITY: Rate limit 체크
    rate_ok, rate_msg = _mail_rate_check()
    if not rate_ok:
        return False, rate_msg

    # 발송
    sent = _smtp_send(to_email, subject, html_body)
    if sent:
        _mail_rate_record()
        return True, "발송 성공"
    return False, "SMTP 발송 실패"


def _strip_image_exif(file_bytes: bytes) -> bytes:
    """SECURITY: 이미지 EXIF 데이터 제거 (Pillow 사용)."""
    if not _PILLOW_OK:
        return file_bytes
    try:
        img = PILImage.open(io.BytesIO(file_bytes))
        out = io.BytesIO()
        # SECURITY: exif 데이터 없이 저장
        img.save(out, format=img.format or "JPEG")
        return out.getvalue()
    except Exception:
        return file_bytes


def _mask_email_for_log(email: str) -> str:
    """SECURITY: 로그용 이메일 마스킹. abc***@gmail.com"""
    if not email or "@" not in email:
        return "***"
    local, domain = email.rsplit("@", 1)
    if len(local) <= 3:
        return f"{local[0]}**@{domain}"
    return f"{local[:3]}***@{domain}"


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


# ── Profile Matching + Bulk Send ─────────────────────────────────────────────

# 지역 매핑: area_prefs 키워드 → client_inquiries.location 매칭값
_REGION_MAP: dict[str, list[str]] = {
    "서울": ["서울", "Seoul", "강남", "강북", "송파", "마포", "종로", "영등포", "서초", "용산", "성동", "광진"],
    "경기": ["경기", "Gyeonggi", "수원", "성남", "용인", "안양", "부천", "화성", "안산", "고양", "일산", "파주", "이천", "평택", "분당", "판교"],
    "인천": ["인천", "Incheon"],
    "부산": ["부산", "Busan"],
    "대구": ["대구", "Daegu"],
    "대전": ["대전", "Daejeon"],
    "광주": ["광주", "Gwangju"],
    "울산": ["울산", "Ulsan"],
    "세종": ["세종", "Sejong"],
    "강원": ["강원", "Gangwon", "춘천", "원주", "강릉"],
    "충북": ["충북", "충청북도", "Chungbuk", "청주", "충주"],
    "충남": ["충남", "충청남도", "Chungnam", "천안", "아산"],
    "전북": ["전북", "전라북도", "Jeonbuk", "전주", "익산", "군산"],
    "전남": ["전남", "전라남도", "Jeonnam", "목포", "순천", "여수"],
    "경북": ["경북", "경상북도", "Gyeongbuk", "포항", "구미", "경주", "김천"],
    "경남": ["경남", "경상남도", "Gyeongnam", "창원", "김해", "진주", "거제"],
    "제주": ["제주", "Jeju"],
}

# 대상 연령 매핑: target/target_age → teaching_age 매칭
_TARGET_MAP: dict[str, list[str]] = {
    "유치": ["Kindergarten", "킨디", "유치원", "유아", "Kinder", "Pre-K", "PreK"],
    "초등": ["Elementary", "초등학교", "Primary", "초등"],
    "중등": ["Middle", "중학교", "중등", "Junior"],
    "고등": ["High", "고등학교", "고등", "Senior"],
    "성인": ["Adult", "성인", "University", "대학", "Corporate", "기업"],
    "전체": ["All", "전체", "Any"],
}


class MatchingEmployersQuery(BaseModel):
    candidate_id: str


class ProfileBroadcastBody(BaseModel):
    candidate_id: str
    employer_ids: list[int]
    custom_subject: Optional[str] = None
    custom_body: Optional[str] = None


def _match_region(area_prefs: str, location: str) -> bool:
    """후보자 area_prefs와 employer location 매칭."""
    if not area_prefs or not location:
        return False
    area_lower = area_prefs.lower()
    loc_lower = location.lower()
    # "Anywhere" / "전국" → 모든 지역 매칭
    if any(kw in area_lower for kw in ["anywhere", "전국", "any", "flexible"]):
        return True
    for region_key, keywords in _REGION_MAP.items():
        area_hit = any(kw.lower() in area_lower for kw in [region_key] + keywords)
        loc_hit = any(kw.lower() in loc_lower for kw in [region_key] + keywords)
        if area_hit and loc_hit:
            return True
    return False


def _match_target(target: str, target_age: str, teaching_age: str) -> bool:
    """후보자 target/target_age와 employer teaching_age 매칭."""
    if not teaching_age:
        return False
    cand_parts = f"{target or ''} {target_age or ''}".lower()
    emp_lower = teaching_age.lower()
    # 전체/Any → 모든 대상 매칭
    if any(kw in cand_parts for kw in ["all", "any", "전체"]):
        return True
    if any(kw in emp_lower for kw in ["all", "any", "전체"]):
        return True
    for _tgt_key, keywords in _TARGET_MAP.items():
        cand_hit = any(kw.lower() in cand_parts for kw in keywords)
        emp_hit = any(kw.lower() in emp_lower for kw in keywords)
        if cand_hit and emp_hit:
            return True
    return False


@app.get("/api/admin/matching/employers", tags=["admin"])
async def admin_matching_employers(request: Request, candidate_id: str):
    """후보자 지역/대상 기반 employer 매칭 목록."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        # 후보자 조회
        cand = conn.execute(
            "SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,)
        ).fetchone()
        if not cand:
            raise HTTPException(status_code=404, detail="Candidate not found")
        cand = dict(cand)

        area_prefs = cand.get("area_prefs", "") or ""
        target = cand.get("target", "") or ""
        target_age = cand.get("target_age", "") or ""

        # 모든 employer (client_inquiries) 조회 — email 있는 것만
        employers = conn.execute(
            "SELECT * FROM client_inquiries WHERE email IS NOT NULL AND email != '' ORDER BY id DESC"
        ).fetchall()

        # 이미 발송된 기록 조회
        sent_rows = conn.execute(
            "SELECT employer_id FROM profile_sends WHERE candidate_id = ?",
            (candidate_id,)
        ).fetchall()
        sent_ids = {r["employer_id"] for r in sent_rows}

        matched = []
        unmatched = []
        for emp in employers:
            emp_d = dict(emp)
            emp_loc = emp_d.get("location", "") or ""
            emp_teach = emp_d.get("teaching_age", "") or ""

            region_ok = _match_region(area_prefs, emp_loc)
            target_ok = _match_target(target, target_age, emp_teach)
            emp_d["_region_match"] = region_ok
            emp_d["_target_match"] = target_ok
            emp_d["_already_sent"] = emp_d["id"] in sent_ids

            # 매칭 점수: region+target=2, region만=1, target만=1, 없음=0
            score = int(region_ok) + int(target_ok)
            emp_d["_match_score"] = score

            if score > 0:
                matched.append(emp_d)
            else:
                unmatched.append(emp_d)

        # 점수순 정렬 (높은 것 먼저)
        matched.sort(key=lambda x: (-x["_match_score"], x.get("school_name", "") or ""))

        return ok(data={
            "candidate": {
                "candidate_id": cand.get("candidate_id", ""),
                "full_name": cand.get("full_name", ""),
                "nationality": cand.get("nationality", ""),
                "target": target,
                "target_age": target_age,
                "area_prefs": area_prefs,
                "experience": cand.get("experience", ""),
                "education_level": cand.get("education_level", ""),
                "certification": cand.get("certification", ""),
                "visa_type": cand.get("visa_type", ""),
                "start_date": cand.get("start_date", ""),
                "photo_url": cand.get("photo_url", ""),
                "dob": cand.get("dob", ""),
                "gender": cand.get("gender", ""),
            },
            "matched": matched,
            "unmatched": unmatched,
            "total_matched": len(matched),
            "total_unmatched": len(unmatched),
        })
    finally:
        conn.close()


@app.post("/api/admin/matching/send-profile", tags=["admin"])
async def admin_matching_send_profile(request: Request, body: ProfileBroadcastBody):
    """매칭된 employer들에게 후보자 프로필 일괄 발송 (PII 제외)."""
    _check_admin(request)
    if not body.employer_ids:
        raise HTTPException(status_code=400, detail="employer_ids가 비어 있습니다.")

    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        # 후보자 조회
        cand = conn.execute(
            "SELECT * FROM candidates WHERE candidate_id = ?", (body.candidate_id,)
        ).fetchone()
        if not cand:
            raise HTTPException(status_code=404, detail="Candidate not found")
        cand_d = dict(cand)

        # 프로필 카드 생성 (PII 제외)
        card_html = _build_profile_card(cand_d)

        # 템플릿 로드
        tpl = conn.execute(
            "SELECT subject, body_html FROM email_templates WHERE template_key = 'profile_broadcast'"
        ).fetchone()
        if not tpl:
            raise HTTPException(status_code=404, detail="profile_broadcast template not found")

        base_subject = body.custom_subject or tpl["subject"]
        base_body = body.custom_body or tpl["body_html"]

        sent_count = 0
        fail_count = 0
        results = []

        for emp_id in body.employer_ids:
            emp = conn.execute(
                "SELECT id, email, school_name, contact_name FROM client_inquiries WHERE id = ?",
                (emp_id,)
            ).fetchone()
            if not emp or not emp["email"]:
                continue

            school = emp["school_name"] or "School"
            to_email = emp["email"]

            # 템플릿 변수 치환
            html = base_body.replace("{{profile_cards}}", card_html)
            html = html.replace("{{school_name}}", school)
            html = html.replace("{{contact_name}}", emp["contact_name"] or "")
            html = re.sub(r"\{\{\w+\}\}", "", html)

            subject = f"{base_subject} - {school}" if school != "School" else base_subject

            sent = _smtp_send(to_email, subject, html)
            status_val = "sent" if sent else "failed"
            if sent:
                sent_count += 1
            else:
                fail_count += 1

            # 발송 로그 기록
            conn.execute(
                """INSERT INTO profile_sends (candidate_id, employer_id, school_name, to_email, status)
                   VALUES (?, ?, ?, ?, ?)""",
                (body.candidate_id, emp_id, school, to_email, status_val)
            )
            results.append({"employer_id": emp_id, "school": school, "email": to_email, "status": status_val})

        conn.commit()

        return ok(
            message=f"Profile broadcast: {sent_count} sent, {fail_count} failed",
            data={"sent": sent_count, "failed": fail_count, "results": results}
        )
    finally:
        conn.close()


@app.get("/api/admin/matching/history", tags=["admin"])
async def admin_matching_history(request: Request, candidate_id: str = ""):
    """프로필 발송 이력 조회."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        if candidate_id:
            rows = conn.execute(
                "SELECT * FROM profile_sends WHERE candidate_id = ? ORDER BY sent_at DESC",
                (candidate_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM profile_sends ORDER BY sent_at DESC LIMIT 200"
            ).fetchall()
        return ok(data=[dict(r) for r in rows])
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
    category: Optional[str] = None,
):
    if board not in _BOARDS:
        raise HTTPException(404, "Board not found")
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    if category:
        rows = conn.execute(
            """SELECT id, title, body, author_hash, pinned, views, created_at,
                      content_type, sort_order, category, substr(body, 1, 200) AS preview
               FROM community_posts
               WHERE board=? AND is_deleted=0 AND category=?
               ORDER BY pinned DESC, sort_order DESC, created_at DESC
               LIMIT ? OFFSET ?""",
            (board, category, limit, offset),
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM community_posts WHERE board=? AND is_deleted=0 AND category=?",
            (board, category),
        ).fetchone()[0]
    else:
        rows = conn.execute(
            """SELECT id, title, author_hash, pinned, views, created_at,
                      content_type, sort_order, substr(body, 1, 200) AS preview
               FROM community_posts
               WHERE board=? AND is_deleted=0
               ORDER BY pinned DESC, sort_order DESC, created_at DESC
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
        """SELECT id, board, title, body, pinned, views, created_at, content_type
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
    content_type: str = Field("markdown", pattern=r"^(markdown|html)$")
    category: Optional[str] = Field(None, max_length=50)


@app.post("/api/community/{board}", status_code=201, tags=["community"])
async def community_create(board: str, post: CommunityPost, request: Request):
    if board not in _BOARDS:
        raise HTTPException(404, "Board not found")
    ip_hash = _ip_hash(request)
    if not _rate_ok(ip_hash):
        raise HTTPException(429, "Too many posts. Please wait a few minutes.")

    # 콘텐츠 타입에 따라 처리
    _tag_re = re.compile(r'<[^>]+>')
    clean_title = _tag_re.sub('', post.title.strip())  # 제목은 항상 strip
    if post.content_type == 'html':
        clean_body = _sanitize_html(post.body.strip())
    else:
        clean_body = _tag_re.sub('', post.body.strip())

    # 게시글 본문에서 연락처 PII 차단 (태그 제거 후 검사)
    _pii_check = re.compile(r'01[016789][- ]?\d{3,4}[- ]?\d{4}|[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
    pii_check_body = _tag_re.sub('', clean_body)  # PII 체크는 태그 제거 후 텍스트만
    if _pii_check.search(pii_check_body) or _pii_check.search(clean_title):
        raise HTTPException(400, "Phone numbers and email addresses are not allowed in posts.")

    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    cur = conn.execute(
        "INSERT INTO community_posts (board, title, body, author_hash, content_type, category) VALUES (?,?,?,?,?,?)",
        (board, clean_title, clean_body, ip_hash, post.content_type, post.category),
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
    content_type: Optional[str] = Field(None, pattern=r"^(markdown|html)$")
    category: Optional[str] = Field(None, max_length=50)


class ReorderItem(BaseModel):
    id: int
    sort_order: int


class ReorderRequest(BaseModel):
    items: list[ReorderItem]


@app.patch("/api/admin/community-reorder/{board}", tags=["admin"])
async def admin_reorder_posts(board: str, body: ReorderRequest, request: Request):
    """게시글 정렬 순서 일괄 업데이트 (관리자 전용)."""
    _check_admin(request)
    if board not in _BOARDS:
        raise HTTPException(404, "Board not found")
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        for item in body.items:
            conn.execute(
                "UPDATE community_posts SET sort_order=? WHERE id=? AND board=? AND is_deleted=0",
                (item.sort_order, item.id, board),
            )
        conn.commit()
    finally:
        conn.close()
    return ok(message=f"Reordered {len(body.items)} posts")


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
        if body.content_type == 'html':
            params.append(_sanitize_html(body.body.strip()))
        else:
            params.append(_tag_re.sub('', body.body.strip()))
    if body.content_type is not None:
        updates.append("content_type = ?")
        params.append(body.content_type)
    if body.category is not None:
        updates.append("category = ?")
        params.append(body.category)

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
                       content_type, sort_order, substr(body, 1, 200) AS preview
                FROM community_posts
                WHERE {where}
                ORDER BY pinned DESC, sort_order DESC, created_at DESC
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
                "SELECT candidate_id, full_name, email, nationality, mobile_phone, "
                "current_location, target, target_age, desired_salary, experience, "
                "start_date, status, created_at, updated_at "
                "FROM candidates ORDER BY created_at DESC LIMIT 200"
            ).fetchall()
            for c in cands:
                apps.append({
                    "id": c["candidate_id"], "type": "candidate",
                    "name": c["full_name"] or "", "email": c["email"] or "",
                    "nationality": c["nationality"],
                    "phone": c["mobile_phone"],
                    "location": c["current_location"],
                    "target": c["target"],
                    "target_age": c["target_age"],
                    "desired_salary": c["desired_salary"],
                    "experience": c["experience"],
                    "start_date": c["start_date"],
                    "status": c["status"] or "Active",
                    "created_at": c["created_at"] or "",
                    "updated_at": c["updated_at"],
                })

            # 구인자 (client_inquiries) + jobs.job_code LEFT JOIN
            inqs = conn.execute(
                "SELECT ci.id, ci.school_name, ci.contact_name, ci.email, ci.phone, ci.location, "
                "ci.start_date, ci.vacancies, ci.teaching_age, ci.schedule, ci.working_hours, ci.salary_raw, "
                "ci.housing_type, ci.housing_detail, ci.travel_support, ci.benefits, ci.vacation, "
                "ci.sick_leave, ci.meal, ci.memo, ci.notes, ci.assigned_to, ci.inbox_status, ci.submitted_at, "
                "ci.source_file, jm.job_code "
                "FROM client_inquiries ci "
                "LEFT JOIN (SELECT internal_notes, MIN(job_code) AS job_code FROM jobs GROUP BY internal_notes) jm "
                "ON ci.memo = jm.internal_notes "
                "ORDER BY ci.submitted_at DESC"
            ).fetchall()
            for i in inqs:
                apps.append({
                    "id": str(i["id"]), "type": "employer",
                    "name": i["contact_name"] or "", "email": i["email"] or "",
                    "school_name": i["school_name"] or "",
                    "contact_name": i["contact_name"],
                    "job_code": i["job_code"],
                    "source_file": i["source_file"],
                    "phone": i["phone"],
                    "location": i["location"],
                    "start_date": i["start_date"],
                    "vacancies": i["vacancies"],
                    "teaching_age": i["teaching_age"],
                    "schedule": i["schedule"],
                    "working_hours": i["working_hours"],
                    "salary_raw": i["salary_raw"],
                    "housing_type": i["housing_type"],
                    "housing_detail": i["housing_detail"],
                    "travel_support": i["travel_support"],
                    "benefits": i["benefits"],
                    "vacation": i["vacation"],
                    "sick_leave": i["sick_leave"],
                    "meal": i["meal"],
                    "memo": i["memo"],
                    "notes": i["notes"],
                    "assigned_to": i["assigned_to"],
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


def _ensure_interviews_schema():
    """interviews 테이블에 이메일 발송 timestamp 컬럼 추가."""
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    for col in ("email_sent_candidate_at", "email_sent_employer_at"):
        try:
            conn.execute(f"ALTER TABLE interviews ADD COLUMN {col} TEXT")
        except Exception:
            pass
    conn.commit()
    conn.close()


_ensure_interviews_schema()


def _ensure_community_schema():
    """community_posts 테이블에 content_type, sort_order, category 컬럼 추가."""
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    for col_sql in (
        "ALTER TABLE community_posts ADD COLUMN content_type TEXT DEFAULT 'markdown'",
        "ALTER TABLE community_posts ADD COLUMN sort_order INTEGER DEFAULT 0",
        "ALTER TABLE community_posts ADD COLUMN category TEXT DEFAULT NULL",
    ):
        try:
            conn.execute(col_sql)
        except Exception:
            pass
    conn.commit()
    conn.close()


_ensure_community_schema()


# ── HTML Sanitizer (allowlist 기반) ──────────────────────────────────────────

_ALLOWED_TAGS = frozenset({
    "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "a", "img", "strong", "em", "b", "i", "u",
    "br", "hr", "table", "thead", "tbody", "tr", "th", "td",
    "div", "span", "blockquote", "code", "pre", "sub", "sup",
})
_ALLOWED_ATTRS = frozenset({
    "href", "src", "alt", "class", "style", "target", "rel",
    "width", "height", "colspan", "rowspan",
})


def _sanitize_html(html_str: str) -> str:
    """Allowlist 기반 HTML sanitizer. script/iframe/object 등 위험 태그 제거."""
    from html.parser import HTMLParser
    import html as _html_mod

    output: list[str] = []

    class Sanitizer(HTMLParser):
        def __init__(self):
            super().__init__()
            self._skip_depth = 0

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
            tag_lower = tag.lower()
            if tag_lower not in _ALLOWED_TAGS:
                self._skip_depth += 1
                return
            if self._skip_depth > 0:
                return
            safe_attrs = []
            for k, v in attrs:
                if k.lower() in _ALLOWED_ATTRS and v is not None:
                    # href/src에서 javascript: 차단
                    if k.lower() in ("href", "src"):
                        if v.strip().lower().startswith("javascript:"):
                            continue
                    safe_attrs.append(f'{k}="{_html_mod.escape(v, quote=True)}"')
            attr_str = (" " + " ".join(safe_attrs)) if safe_attrs else ""
            if tag_lower in ("br", "hr", "img"):
                output.append(f"<{tag_lower}{attr_str} />")
            else:
                output.append(f"<{tag_lower}{attr_str}>")

        def handle_endtag(self, tag: str):
            tag_lower = tag.lower()
            if tag_lower not in _ALLOWED_TAGS:
                if self._skip_depth > 0:
                    self._skip_depth -= 1
                return
            if self._skip_depth > 0:
                return
            output.append(f"</{tag_lower}>")

        def handle_data(self, data: str):
            if self._skip_depth > 0:
                return
            output.append(_html_mod.escape(data))

        def handle_entityref(self, name: str):
            if self._skip_depth > 0:
                return
            output.append(f"&{name};")

        def handle_charref(self, name: str):
            if self._skip_depth > 0:
                return
            output.append(f"&#{name};")

    parser = Sanitizer()
    parser.feed(html_str)
    return "".join(output)


def _ensure_interview_templates():
    """interview_employer / interview_candidate 이메일 템플릿 시딩."""
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")

    employer_subject = "인터뷰 일정 안내 — {scheduled_at}"
    employer_html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,'Segoe UI','Malgun Gothic',sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#333;line-height:1.7;">
<div style="text-align:center;padding:20px 0;border-bottom:2px solid #1d1d1f;">
<h1 style="margin:0;font-size:24px;color:#1d1d1f;font-weight:700;">BRIDGE</h1>
<p style="margin:4px 0 0;font-size:12px;color:#86868b;">ESL Teacher Recruitment Platform</p>
</div>
<div style="padding:30px 0;">
<p>안녕하세요,</p>
<p>BRIDGE를 통해 채용 후보자 <strong>{candidate_first_name}</strong>님과의 인터뷰가 예정되었습니다.</p>

<div style="background:#f0fdf4;border:1px solid #86efac;padding:20px;margin:24px 0;border-radius:12px;text-align:center;">
<p style="margin:0 0 8px;font-size:18px;font-weight:700;color:#166534;">{scheduled_at}</p>
<a href="{meet_link}" style="display:inline-block;background:#1d1d1f;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;margin-top:12px;">Google Meet 입장</a>
<p style="margin:12px 0 0;font-size:12px;color:#6b7280;">링크: <a href="{meet_link}" style="color:#0071e3;">{meet_link}</a></p>
</div>

<div style="background:#f5f5f7;padding:20px;margin:24px 0;border-radius:12px;">
<p style="margin:0 0 12px;font-weight:600;color:#1d1d1f;">BRIDGE 서비스 정책 안내</p>
<ul style="margin:0;padding-left:20px;color:#424245;line-height:1.9;">
<li>후보자 개인정보(성, 연락처, 이메일 등)는 BRIDGE 정책에 따라 비공개입니다.</li>
<li>인터뷰 중 후보자에게 개인 연락처를 직접 요청하지 마세요.</li>
<li>채용 진행은 반드시 BRIDGE를 통해 진행해 주세요.</li>
<li>인터뷰 결과는 BRIDGE 담당자에게 회신해 주시면 됩니다.</li>
</ul>
</div>

<div style="background:#fffbeb;border:1px solid #fde68a;padding:20px;margin:24px 0;border-radius:12px;">
<p style="margin:0 0 12px;font-weight:600;color:#92400e;">인터뷰 가이드</p>
<ul style="margin:0;padding-left:20px;color:#424245;line-height:1.9;">
<li>Google Meet '회의 액세스 유형'을 <strong>'열기'</strong>로 설정해 주세요.</li>
<li>예정 시간 2-3분 전에 입장해 주세요.</li>
<li>카메라와 마이크를 미리 테스트해 주세요.</li>
<li>조용하고 밝은 환경에서 진행해 주세요.</li>
</ul>
</div>

<p>일정 변경이 필요하시면 <a href="mailto:bridgejobkr@gmail.com" style="color:#0071e3;">bridgejobkr@gmail.com</a>으로 연락해 주세요.</p>
<p style="color:#6e6e73;margin-top:30px;">감사합니다.<br><strong>BRIDGE Team 드림</strong></p>
</div>
<div style="border-top:1px solid #e5e7eb;padding-top:16px;text-align:center;font-size:12px;color:#86868b;">
<p>The BRIDGE Team &middot; <a href="https://bridgejob.co.kr" style="color:#0071e3;">bridgejob.co.kr</a></p>
</div>
</body></html>"""

    candidate_subject = "Interview Scheduled — {scheduled_at}"
    candidate_html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,'Segoe UI',Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#333;line-height:1.7;">
<div style="text-align:center;padding:20px 0;border-bottom:2px solid #1d1d1f;">
<h1 style="margin:0;font-size:24px;color:#1d1d1f;font-weight:700;">BRIDGE</h1>
<p style="margin:4px 0 0;font-size:12px;color:#86868b;">ESL Teacher Recruitment Platform</p>
</div>
<div style="padding:30px 0;">
<p>Dear {candidate_first_name},</p>
<p>Great news! Your interview has been scheduled through BRIDGE.</p>

<div style="background:#f0fdf4;border:1px solid #86efac;padding:20px;margin:24px 0;border-radius:12px;text-align:center;">
<p style="margin:0 0 8px;font-size:18px;font-weight:700;color:#166534;">{scheduled_at}</p>
<a href="{meet_link}" style="display:inline-block;background:#1d1d1f;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;margin-top:12px;">Join Google Meet</a>
<p style="margin:12px 0 0;font-size:12px;color:#6b7280;">Link: <a href="{meet_link}" style="color:#0071e3;">{meet_link}</a></p>
</div>

<div style="background:#eff6ff;border:1px solid #bfdbfe;padding:20px;margin:24px 0;border-radius:12px;">
<p style="margin:0 0 12px;font-weight:600;color:#1e40af;">Privacy Protocol</p>
<ul style="margin:0;padding-left:20px;color:#424245;line-height:1.9;">
<li>The employer will only know your first name during the interview.</li>
<li>Your personal contact information is protected by BRIDGE.</li>
<li>Do not share your phone number, personal email, or address directly.</li>
<li>All communication should go through BRIDGE.</li>
</ul>
</div>

<div style="background:#f5f5f7;padding:20px;margin:24px 0;border-radius:12px;">
<p style="margin:0 0 12px;font-weight:600;color:#1d1d1f;">Essential Guide</p>
<ul style="margin:0;padding-left:20px;color:#424245;line-height:1.9;">
<li>Test your camera and microphone beforehand</li>
<li>Find a quiet, well-lit space</li>
<li>Dress professionally (business casual or above)</li>
<li>Have your resume and any documents ready</li>
<li>Join the meeting 2-3 minutes early</li>
</ul>
</div>

<p>If you need to reschedule, please email <a href="mailto:bridgejobkr@gmail.com" style="color:#0071e3;">bridgejobkr@gmail.com</a> as soon as possible.</p>
<p style="color:#6e6e73;margin-top:30px;">Good luck!<br><strong>BRIDGE Team</strong></p>
</div>
<div style="border-top:1px solid #e5e7eb;padding-top:16px;text-align:center;font-size:12px;color:#86868b;">
<p>The BRIDGE Team &middot; <a href="https://bridgejob.co.kr" style="color:#0071e3;">bridgejob.co.kr</a></p>
</div>
</body></html>"""

    # profile_broadcast 템플릿 (구인자에게 후보자 프로필 발송용)
    profile_subject = "BRIDGE — 채용 후보자 프로필 안내"
    profile_html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,'Segoe UI','Malgun Gothic',sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#333;line-height:1.7;">
<div style="text-align:center;padding:20px 0;border-bottom:2px solid #1d1d1f;">
<h1 style="margin:0;font-size:24px;color:#1d1d1f;font-weight:700;">BRIDGE</h1>
<p style="margin:4px 0 0;font-size:12px;color:#86868b;">ESL Teacher Recruitment Platform</p>
</div>
<div style="padding:30px 0;">
<p>안녕하세요, {{contact_name}}님</p>
<p>BRIDGE에서 {{school_name}} 조건에 맞는 채용 후보자를 안내드립니다.</p>

<div style="margin:24px 0;">
{{profile_cards}}
</div>

{{download_link}}

<div style="background:#f5f5f7;padding:20px;margin:24px 0;border-radius:12px;">
<p style="margin:0 0 12px;font-weight:600;color:#1d1d1f;">안내 사항</p>
<ul style="margin:0;padding-left:20px;color:#424245;line-height:1.9;">
<li>후보자 개인정보(성명, 연락처, 이메일 등)는 BRIDGE 정책에 따라 비공개입니다.</li>
<li>채용 진행은 반드시 BRIDGE를 통해 진행해 주세요.</li>
<li>관심 있는 후보자가 있으시면 이 이메일에 회신해 주세요.</li>
<li>인터뷰 일정을 잡아드리겠습니다.</li>
</ul>
</div>

<p>궁금한 점이 있으시면 <a href="mailto:bridgejobkr@gmail.com" style="color:#0071e3;">bridgejobkr@gmail.com</a>으로 연락해 주세요.</p>
<p style="color:#6e6e73;margin-top:30px;">감사합니다.<br><strong>BRIDGE Team 드림</strong></p>
</div>
<div style="border-top:1px solid #e5e7eb;padding-top:16px;text-align:center;font-size:12px;color:#86868b;">
<p>The BRIDGE Team &middot; <a href="https://bridgejob.co.kr" style="color:#0071e3;">bridgejob.co.kr</a></p>
<p style="font-size:10px;color:#aeaeb2;">이 이메일은 BRIDGE 채용 서비스의 일환으로 발송되었습니다.</p>
</div>
</body></html>"""

    for key, subj, body in [
        ("interview_employer", employer_subject, employer_html),
        ("interview_candidate", candidate_subject, candidate_html),
        ("profile_broadcast", profile_subject, profile_html),
    ]:
        conn.execute(
            """INSERT INTO email_templates (template_key, subject, body_html, updated_at)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(template_key) DO NOTHING""",
            (key, subj, body),
        )
    conn.commit()
    conn.close()


def _ensure_profile_sends_schema():
    """profile_sends 테이블 생성 (없으면)."""
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS profile_sends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id TEXT NOT NULL,
            employer_id INTEGER NOT NULL,
            school_name TEXT,
            to_email TEXT,
            status TEXT DEFAULT 'sent',
            sent_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


_ensure_interview_templates()
_ensure_profile_sends_schema()


class InterviewCreate(BaseModel):
    candidate_name:  str = Field("", max_length=200)
    candidate_email: str = Field("", max_length=200)
    employer_name:   str = Field("", max_length=200)
    employer_email:  str = Field("", max_length=200)
    interview_date:  str = Field(..., min_length=8, max_length=20)
    interview_time:  str = Field(..., min_length=3, max_length=20)
    meet_link:       str = Field(..., min_length=5, max_length=500)
    notes:           str = Field("", max_length=2000)


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
    """인터뷰 생성 (이메일은 별도 엔드포인트로 발송)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
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
    finally:
        conn.close()
    return ok(
        data={"id": interview_id},
        message=f"Interview #{interview_id} created",
    )


def _render_interview_email(interview: dict, target: str):
    """인터뷰 이메일 렌더링. (subject, html, to_email) 반환."""
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        tpl_key = f"interview_{target}"
        row = conn.execute(
            "SELECT subject, body_html FROM email_templates WHERE template_key = ?",
            (tpl_key,),
        ).fetchone()
        if not row:
            raise HTTPException(404, f"Template '{tpl_key}' not found")
    finally:
        conn.close()

    candidate_name = interview.get("candidate_name") or ""
    first_name = candidate_name.split(" ")[0] if candidate_name.strip() else (
        "Candidate" if target == "candidate" else "후보자"
    )
    scheduled_at = f"{interview['interview_date']} {interview['interview_time']} KST"
    meet_link = interview.get("meet_link") or ""
    to_email = interview.get("candidate_email") if target == "candidate" else interview.get("employer_email")

    employer_name = interview.get("employer_name") or ""

    replacements = {
        "{candidate_first_name}": first_name,
        "{candidate_name}": candidate_name,
        "{scheduled_at}": scheduled_at,
        "{meet_link}": meet_link,
        "{employer_name}": employer_name,
    }

    subject = row["subject"]
    html = row["body_html"]
    for k, v in replacements.items():
        subject = subject.replace(k, v)
        html = html.replace(k, v)

    # PII 격리 체크
    candidate_email = interview.get("candidate_email") or ""
    employer_email = interview.get("employer_email") or ""
    if target == "employer":
        # 고용주 메일에 후보자 이메일/전화 포함 시 차단
        if candidate_email and candidate_email in html:
            raise HTTPException(400, "PII violation: candidate email found in employer template")
    elif target == "candidate":
        # 후보자 메일에 고용주 이메일/전화 포함 시 차단
        if employer_email and employer_email in html:
            raise HTTPException(400, "PII violation: employer email found in candidate template")

    return subject, html, to_email


class InterviewSendEmail(BaseModel):
    target: str = Field(..., pattern=r"^(candidate|employer)$")


@app.get("/api/admin/interviews/{interview_id}/preview-email", tags=["admin"])
async def admin_preview_interview_email(interview_id: int, target: str, request: Request):
    """인터뷰 이메일 미리보기."""
    _check_admin(request)
    if target not in ("candidate", "employer"):
        raise HTTPException(400, "target must be 'candidate' or 'employer'")
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        iv = conn.execute("SELECT * FROM interviews WHERE id=? AND is_deleted=0", (interview_id,)).fetchone()
    finally:
        conn.close()
    if not iv:
        raise HTTPException(404, "Interview not found")
    subject, html, to_email = _render_interview_email(dict(iv), target)
    return ok(data={"subject": subject, "body_html": html, "to_email": to_email or ""})


@app.post("/api/admin/interviews/{interview_id}/send-email", tags=["admin"])
async def admin_send_interview_email(interview_id: int, body: InterviewSendEmail, request: Request):
    """인터뷰 이메일 발송."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        iv = conn.execute("SELECT * FROM interviews WHERE id=? AND is_deleted=0", (interview_id,)).fetchone()
        if not iv:
            conn.close()
            raise HTTPException(404, "Interview not found")
        subject, html, to_email = _render_interview_email(dict(iv), body.target)
        if not to_email:
            conn.close()
            raise HTTPException(400, f"No {body.target} email address on this interview")
        sent = _smtp_send(to_email, subject, html)
        if not sent:
            conn.close()
            return err("이메일 발송 실패 (SMTP 설정 확인)", 500)
        sent_cols = {
            "employer": ("email_sent_employer", "school_email_sent", "school_email_sent_at"),
            "candidate": ("email_sent_candidate", "candidate_email_sent", "candidate_email_sent_at"),
        }
        old_col, new_col, new_at_col = sent_cols.get(body.target, ("email_sent_candidate", "candidate_email_sent", "candidate_email_sent_at"))
        conn.execute(
            f"UPDATE interviews SET {old_col}=1, {new_col}=1, {new_at_col}=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (interview_id,),
        )
        conn.commit()
    finally:
        conn.close()
    return ok(data={"sent_to": to_email, "target": body.target}, message=f"{body.target} 이메일 발송 완료")


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
    "community_image": (
        5 * 1024 * 1024,
        {".jpg", ".jpeg", ".png", ".gif", ".webp"},
        [b"\xff\xd8\xff", b"\x89PNG", b"GIF8", b"RIFF"],
    ),
    "community_file": (
        10 * 1024 * 1024,
        {".pdf", ".doc", ".docx", ".xlsx", ".ppt", ".pptx", ".txt", ".zip"},
        [b"%PDF", b"\xd0\xcf\x11\xe0", b"PK"],
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
    entity_type: 'candidate' | 'inquiry' | 'community'
    file_type: 'photo' | 'cv' | 'cover_letter' | 'certificate' | 'video' | 'attachment' | 'community_image' | 'community_file'
    """
    if entity_type not in ("candidate", "inquiry", "community"):
        raise HTTPException(400, "entity_type must be 'candidate', 'inquiry', or 'community'")
    if entity_type == "community":
        _check_admin(request)

    if not _rate_ok(_ip_hash(request), window=60, max_posts=30):
        raise HTTPException(429, "Too many uploads. Please slow down.")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file.")

    ext = _validate_file(data, file.filename or "file", file_type)

    # Build directory
    dir_name = "candidates" if entity_type == "candidate" else ("community" if entity_type == "community" else "inquiries")
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


@app.post("/api/admin/upload-image", tags=["admin"])
async def admin_upload_editor_image(
    request: Request,
    file: UploadFile = FastFile(...),
):
    """에디터 이미지 업로드 (관리자 전용). 서버에 저장 후 URL 반환."""
    _check_admin(request)
    if not _rate_ok(_ip_hash(request), window=60, max_posts=30):
        raise HTTPException(429, "Too many uploads.")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file.")
    ext = _validate_file(data, file.filename or "image.png", "community_image")
    img_dir = _UPLOAD_BASE / "editor"
    img_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{uuid.uuid4().hex[:12]}{ext}"
    file_path = img_dir / fname
    file_path.write_bytes(data)
    file_url = f"/uploads/editor/{fname}"
    return ok(data={"url": file_url}, message="Image uploaded")


@app.get("/api/admin/files/{entity_type}/{entity_id}", tags=["admin"])
async def admin_list_files(entity_type: str, entity_id: str, request: Request):
    """관리자: 엔티티의 업로드된 파일 목록."""
    _check_admin(request)
    if entity_type not in ("candidate", "inquiry", "community"):
        raise HTTPException(400, "entity_type must be 'candidate', 'inquiry', or 'community'")
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


# ── Admin: Jobs v2 (BRJ ID 시스템) ───────────────────────────────────────────

_JOB_REGION_MAP = {
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

_JOB_REGION_NAMES = {
    "SE": "서울", "BS": "부산", "DG": "대구", "IC": "인천",
    "GJ": "광주", "DJ": "대전", "US": "울산", "SJ": "세종",
    "GG": "경기", "GW": "강원", "CB": "충북", "CN": "충남",
    "JB": "전북", "JN": "전남", "KB": "경북", "KN": "경남",
    "JJ": "제주", "XX": "기타",
}


def _detect_region(text: str) -> str:
    if not text:
        return "XX"
    for key, code in _JOB_REGION_MAP.items():
        if key.lower() in text.lower():
            return code
    return "XX"


def _next_brj_id(conn, region_code: str) -> str:
    yymm = datetime.now(timezone.utc).strftime("%y%m")
    prefix = f"BRJ-{region_code}-{yymm}-"
    row = conn.execute(
        "SELECT brj_id FROM jobs WHERE brj_id LIKE ? ORDER BY brj_id DESC LIMIT 1",
        (f"{prefix}%",),
    ).fetchone()
    seq = int(row[0].split("-")[-1]) + 1 if row else 1
    return f"{prefix}{seq:03d}"


_JOB_WRITABLE = {
    "city", "district", "location", "teaching_age", "class_size",
    "working_hours", "daily_hours", "start_date", "salary_raw",
    "salary_min", "salary_max", "salary_krw", "salary_negotiable",
    "vacation", "vacation_days", "housing", "housing_type", "housing_detail",
    "benefits", "native_count", "teach_hrs_week", "teaching_hours_weekly",
    "is_hot", "is_part_time", "status",
    "enc_employer_name", "enc_contact_name", "enc_contact_phone",
    "enc_contact_email", "enc_contact_kakao", "employer_display_name",
    "visa_sponsorship", "f_visa_welcome", "kyopo_welcome",
    "degree_requirement", "korea_resident_only",
    "raw_text", "raw_source", "parse_confidence", "parse_warnings",
    "internal_notes", "recruiter_memo",
}


@app.get("/api/admin/jobs/v2", tags=["admin"])
async def admin_list_jobs_v2(
    request: Request,
    status: Optional[str] = None,
    region: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """채용공고 v2 전체 목록 (BRJ ID + 관리자 필드 포함)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        where = ["is_deleted = 0"]
        params: list[Any] = []
        if status:
            where.append("status = ?")
            params.append(status)
        if region:
            where.append("region = ?")
            params.append(region)
        if search:
            s = f"%{search.strip()[:50]}%"
            where.append(
                "(brj_id LIKE ? OR job_code LIKE ? OR city LIKE ? OR location LIKE ? OR employer_display_name LIKE ?)"
            )
            params.extend([s, s, s, s, s])
        w = " AND ".join(where)
        total = conn.execute(f"SELECT COUNT(*) FROM jobs WHERE {w}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM jobs WHERE {w} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        data = []
        for r in rows:
            d = dict(r)
            for k in list(d.keys()):
                if isinstance(d[k], bytes):
                    d[k] = None
            data.append(d)
        return ok(data={"jobs": data, "total": total})
    finally:
        conn.close()


@app.get("/api/admin/jobs/v2/{brj_id}", tags=["admin"])
async def admin_get_job_v2(brj_id: str, request: Request):
    """채용공고 상세 조회 (BRJ ID)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM jobs WHERE brj_id = ? AND is_deleted = 0", (brj_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Job not found")
        d = dict(row)
        for k in list(d.keys()):
            if isinstance(d[k], bytes):
                d[k] = None
        return ok(data=d)
    finally:
        conn.close()


@app.post("/api/admin/jobs/v2", status_code=201, tags=["admin"])
async def admin_create_job_v2(request: Request, body: dict):
    """새 채용공고 등록 (BRJ ID 자동 생성)."""
    _check_admin(request)
    if not _rate_ok(_ip_hash(request)):
        raise HTTPException(429, "잠시 후 다시 시도해주세요.")
    record = {k: v for k, v in body.items() if k in _JOB_WRITABLE and v is not None}
    region = body.get("region") or _detect_region(
        record.get("city", "") or record.get("location", "")
    )
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        brj_id = _next_brj_id(conn, region)
        max_row = conn.execute("SELECT MAX(id) FROM jobs").fetchone()
        job_code = f"Job.{(max_row[0] or 0) + 1001}"
        record.update({
            "brj_id": brj_id, "job_code": job_code,
            "region": region, "region_name": _JOB_REGION_NAMES.get(region, "기타"),
            "status": record.get("status", "open"),
            "is_deleted": 0, "is_hot": record.get("is_hot", 0),
            "created_at": now, "seq": 1,
        })
        cols = ", ".join(record.keys())
        ph = ", ".join("?" for _ in record)
        conn.execute(f"INSERT INTO jobs ({cols}) VALUES ({ph})", list(record.values()))
        conn.commit()
        _maybe_auto_backup()
        return ok(data={"brj_id": brj_id, "job_code": job_code}, message=f"채용공고 {brj_id} 생성 완료")
    finally:
        conn.close()


@app.patch("/api/admin/jobs/v2/{brj_id}", tags=["admin"])
async def admin_update_job_v2(brj_id: str, request: Request, body: dict):
    """채용공고 수정 (BRJ ID)."""
    _check_admin(request)
    updates = {k: v for k, v in body.items() if k in _JOB_WRITABLE}
    if not updates:
        raise HTTPException(400, "수정할 항목이 없습니다.")
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        row = conn.execute(
            "SELECT id FROM jobs WHERE brj_id = ? AND is_deleted = 0", (brj_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Job not found")
        set_clause = ", ".join(f"{k}=?" for k in updates)
        conn.execute(
            f"UPDATE jobs SET {set_clause} WHERE brj_id = ?",
            list(updates.values()) + [brj_id],
        )
        conn.commit()
        _maybe_auto_backup()
        return ok(message=f"채용공고 {brj_id} 수정 완료")
    finally:
        conn.close()


@app.delete("/api/admin/jobs/v2/{brj_id}", tags=["admin"])
async def admin_soft_delete_job_v2(brj_id: str, request: Request):
    """채용공고 soft delete (BRJ ID)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        row = conn.execute(
            "SELECT id FROM jobs WHERE brj_id = ? AND is_deleted = 0", (brj_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Job not found")
        conn.execute("UPDATE jobs SET is_deleted = 1 WHERE brj_id = ?", (brj_id,))
        conn.commit()
        _maybe_auto_backup()
        return ok(message=f"채용공고 {brj_id} 삭제 완료")
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


# ── Admin: Site Partners 관리 ──────────────────────────────────────────────────

def _ensure_site_partners_table():
    """site_partners 테이블 생성 (없으면)."""
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS site_partners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'academy',
            logo_url TEXT,
            website TEXT,
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            is_deleted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 기존 하드코딩 파트너가 비어있으면 시드 데이터 삽입
    count = conn.execute("SELECT COUNT(*) FROM site_partners").fetchone()[0]
    if count == 0:
        academies = [
            'Chungdahm Learning', 'YBM', 'Warwick Franklin', 'Poly',
            'Wall Street English', 'April', 'Hillside IYASkola', 'Sogang SLP',
            'Fast Track Kids', 'Avalon', 'DYB Choisun', 'Rise Korea',
            'JLS Jungsang', 'Real Class', 'Siwon School',
            'Korea University Foreign Language Center', 'Crecerse',
            'LinguaEdu', 'Simson Edu', 'LexKim English', 'MiEdu',
            'Twinkle Language', 'SDA', 'Wiz Island', 'Kids College',
        ]
        schools = [
            'Busan International Foreign School', 'Dalton School',
            'Taejon Christian International School', 'Busan Foreign School',
            'Gyeonggi English Village', 'Dulwich College Seoul',
            'Korea International School', 'Chadwick International',
            'Gangwon English Camp', 'Dwight School Seoul',
            'Yongsan International School of Seoul', 'Saint Paul Academy',
            'Paju English Village', 'Seoul Scholars International',
            'North London Collegiate School', 'Seoul Foreign School',
            'Daegu International School', 'British Council Korea',
            'Gyeonggi International School', 'Jeju International School',
            'Mountain Cherry Academy', 'Seoul International School',
        ]
        for i, name in enumerate(academies):
            conn.execute(
                "INSERT INTO site_partners (name, category, sort_order) VALUES (?, 'academy', ?)",
                (name, i)
            )
        for i, name in enumerate(schools):
            conn.execute(
                "INSERT INTO site_partners (name, category, sort_order) VALUES (?, 'school', ?)",
                (name, i)
            )
        conn.commit()
    conn.close()

_ensure_site_partners_table()


class PartnerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field('academy', pattern=r'^(academy|school)$')
    logo_url: Optional[str] = None
    website: Optional[str] = None
    sort_order: Optional[int] = 0


class PartnerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = Field(None, pattern=r'^(academy|school)$')
    logo_url: Optional[str] = None
    website: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[int] = Field(None, ge=0, le=1)


@app.get("/api/partners", tags=["public"])
async def public_list_partners():
    """공개 파트너 목록 (활성 파트너만)."""
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, name, category, logo_url, website, sort_order "
            "FROM site_partners WHERE is_active=1 AND is_deleted=0 ORDER BY sort_order, name"
        ).fetchall()
        return ok(data={"partners": [dict(r) for r in rows]})
    finally:
        conn.close()


@app.get("/api/admin/partners", tags=["admin"])
async def admin_list_partners(request: Request):
    """파트너 목록 (관리자 — 비활성 포함)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM site_partners WHERE is_deleted=0 ORDER BY sort_order, name"
        ).fetchall()
        return ok(data={"partners": [dict(r) for r in rows]})
    finally:
        conn.close()


@app.post("/api/admin/partners", status_code=201, tags=["admin"])
async def admin_create_partner(body: PartnerCreate, request: Request):
    """파트너 추가 (관리자)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        conn.execute(
            "INSERT INTO site_partners (name, category, logo_url, website, sort_order) VALUES (?,?,?,?,?)",
            (body.name, body.category, body.logo_url, body.website, body.sort_order or 0),
        )
        conn.commit()
        return ok(message="Partner created")
    finally:
        conn.close()


@app.put("/api/admin/partners/{partner_id}", tags=["admin"])
async def admin_update_partner(partner_id: int, body: PartnerUpdate, request: Request):
    """파트너 수정 (관리자)."""
    _check_admin(request)
    updates: list[str] = []
    params: list = []
    if body.name is not None:
        updates.append("name=?"); params.append(body.name)
    if body.category is not None:
        updates.append("category=?"); params.append(body.category)
    if body.logo_url is not None:
        updates.append("logo_url=?"); params.append(body.logo_url)
    if body.website is not None:
        updates.append("website=?"); params.append(body.website)
    if body.sort_order is not None:
        updates.append("sort_order=?"); params.append(body.sort_order)
    if body.is_active is not None:
        updates.append("is_active=?"); params.append(body.is_active)
    if not updates:
        raise HTTPException(400, "수정할 항목이 없습니다.")
    updates.append("updated_at=CURRENT_TIMESTAMP")
    params.append(partner_id)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        r = conn.execute(
            "SELECT id FROM site_partners WHERE id=? AND is_deleted=0", (partner_id,)
        ).fetchone()
        if not r:
            raise HTTPException(404, "Partner not found")
        conn.execute(f"UPDATE site_partners SET {', '.join(updates)} WHERE id=?", params)
        conn.commit()
        return ok(message=f"Partner #{partner_id} updated")
    finally:
        conn.close()


@app.delete("/api/admin/partners/{partner_id}", tags=["admin"])
async def admin_delete_partner(partner_id: int, request: Request):
    """파트너 삭제 — soft delete (관리자)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        r = conn.execute(
            "SELECT id FROM site_partners WHERE id=? AND is_deleted=0", (partner_id,)
        ).fetchone()
        if not r:
            raise HTTPException(404, "Partner not found")
        conn.execute("UPDATE site_partners SET is_deleted=1 WHERE id=?", (partner_id,))
        conn.commit()
        return ok(message=f"Partner #{partner_id} deleted")
    finally:
        conn.close()


@app.put("/api/admin/partners/reorder", tags=["admin"])
async def admin_reorder_partners(request: Request):
    """파트너 순서 일괄 변경 (관리자). body: {order: [{id: 1, sort_order: 0}, ...]}"""
    _check_admin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")
    order_list = body.get("order", [])
    if not order_list:
        raise HTTPException(400, "order 필드가 비어있습니다.")
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        for item in order_list:
            pid = item.get("id")
            so = item.get("sort_order")
            if pid is not None and so is not None:
                conn.execute(
                    "UPDATE site_partners SET sort_order=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND is_deleted=0",
                    (so, pid)
                )
        conn.commit()
        return ok(message="Partner order updated")
    finally:
        conn.close()


# ── Admin: Site Settings 관리 ─────────────────────────────────────────────────

def _ensure_site_settings_table():
    """site_settings 테이블 생성 + 초기 데이터 삽입."""
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS site_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 초기 기본값 삽입 (이미 있으면 무시)
    defaults = [
        ('site_name', 'BRIDGE'),
        ('business_number', ''),
        ('company_name', 'BRIDGE Agency'),
        ('ceo_name', ''),
        ('address', ''),
        ('contact_email', 'bridgejobkr@gmail.com'),
        ('contact_phone', ''),
        ('kakao_channel', ''),
        ('instagram', ''),
        ('facebook', ''),
        ('youtube', ''),
        ('blog', ''),
        ('footer_text', '© 2026 BRIDGE Recruitment · bridgejob.co.kr'),
        ('footer_description', 'Korea ESL Recruitment Platform'),
        ('hero_tagline', 'A career that changes your life'),
        ('hero_subtitle', "Korea's #1 ESL recruitment platform — 원어민 영어강사 채용 전문"),
        ('nav_menu', '[{"href":"/community/about","label":"About us"},{"href":"/community/korea","label":"Korea"},{"href":"/community/visa","label":"Visa"},{"href":"/jobs","label":"Job Board"},{"href":"/community/support","label":"Support"},{"href":"/community/support_kr","label":"업무지원"},{"href":"/community","label":"Community"}]'),
        ('nav_cta_1', '{"href":"/apply","label":"Apply"}'),
        ('nav_cta_2', '{"href":"/inquiry","label":"원어민채용의뢰"}'),
    ]
    for key, value in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO site_settings (key, value) VALUES (?, ?)",
            (key, value)
        )
    conn.commit()
    conn.close()

_ensure_site_settings_table()


@app.get("/api/settings", tags=["public"])
async def public_get_settings():
    """공개 사이트 설정 (footer 등)."""
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT key, value FROM site_settings").fetchall()
        settings = {r["key"]: r["value"] for r in rows}
        return ok(data={"settings": settings})
    finally:
        conn.close()


@app.get("/api/admin/settings", tags=["admin"])
async def admin_get_settings(request: Request):
    """관리자 사이트 설정 조회."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT key, value, updated_at FROM site_settings").fetchall()
        settings = {r["key"]: {"value": r["value"], "updated_at": r["updated_at"]} for r in rows}
        return ok(data={"settings": settings})
    finally:
        conn.close()


@app.put("/api/admin/settings", tags=["admin"])
async def admin_update_settings(request: Request):
    """사이트 설정 일괄 업데이트. body: {settings: {key: value, ...}}"""
    _check_admin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")
    settings = body.get("settings", {})
    if not settings:
        raise HTTPException(400, "settings 필드가 비어있습니다.")
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        for key, value in settings.items():
            conn.execute(
                "INSERT INTO site_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
                (str(key), str(value))
            )
        conn.commit()
        return ok(message="Settings updated")
    finally:
        conn.close()


# ── 방문 추적 (Visit Tracking) ────────────────────────────────────────────────

def _ensure_site_visits_table():
    """site_visits 테이블 생성."""
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS site_visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_hash TEXT NOT NULL,
            referrer TEXT,
            channel TEXT,
            search_keyword TEXT,
            landing_page TEXT,
            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,
            utm_term TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_visits_created ON site_visits(created_at)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_visits_channel ON site_visits(channel)
    """)
    conn.commit()
    conn.close()

_ensure_site_visits_table()


def _classify_channel(referrer: str) -> str:
    """referrer URL → 채널 분류."""
    if not referrer:
        return "direct"
    r = referrer.lower()
    if "google." in r:
        return "google"
    if "naver.com" in r or "search.naver" in r:
        return "naver"
    if "daum.net" in r or "search.daum" in r:
        return "daum"
    if "bing.com" in r:
        return "bing"
    if "yahoo." in r:
        return "yahoo"
    if "facebook.com" in r or "fb.com" in r:
        return "facebook"
    if "instagram.com" in r:
        return "instagram"
    if "twitter.com" in r or "t.co" in r or "x.com" in r:
        return "twitter"
    if "reddit.com" in r:
        return "reddit"
    if "youtube.com" in r or "youtu.be" in r:
        return "youtube"
    if "kakao" in r:
        return "kakao"
    if "linkedin.com" in r:
        return "linkedin"
    if "bridgejob" in r:
        return "internal"
    return "other"


def _extract_search_keyword(referrer: str) -> str:
    """referrer URL에서 검색어 추출 (Naver, Daum 등)."""
    if not referrer:
        return ""
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(referrer)
        params = parse_qs(parsed.query)
        # Naver: query=
        for key in ("query", "q", "p", "search_query", "text", "keyword"):
            if key in params:
                return params[key][0]
    except Exception:
        pass
    return ""


@app.post("/api/track", tags=["public"])
async def track_visit(request: Request):
    """페이지 방문 기록 (공개, rate-limited)."""
    ip = _ip_hash(request)
    if not _rate_ok(ip, window=60, max_posts=30):
        return ok(message="ok")  # 조용히 무시

    try:
        body = await request.json()
    except Exception:
        return ok(message="ok")

    referrer = str(body.get("referrer", ""))[:500]
    landing = str(body.get("page", ""))[:200]
    utm_source = str(body.get("utm_source", ""))[:100]
    utm_medium = str(body.get("utm_medium", ""))[:100]
    utm_campaign = str(body.get("utm_campaign", ""))[:100]
    utm_term = str(body.get("utm_term", ""))[:100]

    channel = _classify_channel(referrer)
    keyword = _extract_search_keyword(referrer)

    # UTM term이 있으면 검색어로 사용
    if utm_term and not keyword:
        keyword = utm_term

    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        conn.execute(
            "INSERT INTO site_visits (visitor_hash, referrer, channel, search_keyword, landing_page, "
            "utm_source, utm_medium, utm_campaign, utm_term) VALUES (?,?,?,?,?,?,?,?,?)",
            (ip, referrer, channel, keyword, landing, utm_source, utm_medium, utm_campaign, utm_term)
        )
        conn.commit()
    finally:
        conn.close()
    return ok(message="ok")


@app.get("/api/admin/analytics", tags=["admin"])
async def admin_analytics(request: Request, days: int = Query(30, ge=1, le=365)):
    """방문 분석 데이터 (관리자)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        # 총 방문수
        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM site_visits WHERE created_at >= ?", (cutoff,)
        ).fetchone()["cnt"]

        # 채널별 유입
        channels = conn.execute(
            "SELECT channel, COUNT(*) as cnt FROM site_visits WHERE created_at >= ? "
            "GROUP BY channel ORDER BY cnt DESC", (cutoff,)
        ).fetchall()

        # 검색 키워드 TOP 30
        keywords = conn.execute(
            "SELECT search_keyword, COUNT(*) as cnt FROM site_visits "
            "WHERE created_at >= ? AND search_keyword != '' "
            "GROUP BY search_keyword ORDER BY cnt DESC LIMIT 30", (cutoff,)
        ).fetchall()

        # 인기 랜딩 페이지 TOP 20
        pages = conn.execute(
            "SELECT landing_page, COUNT(*) as cnt FROM site_visits "
            "WHERE created_at >= ? AND landing_page != '' "
            "GROUP BY landing_page ORDER BY cnt DESC LIMIT 20", (cutoff,)
        ).fetchall()

        # 일별 방문 추이 (최근 days일)
        daily = conn.execute(
            "SELECT DATE(created_at) as day, COUNT(*) as cnt FROM site_visits "
            "WHERE created_at >= ? GROUP BY DATE(created_at) ORDER BY day", (cutoff,)
        ).fetchall()

        # UTM 캠페인별
        campaigns = conn.execute(
            "SELECT utm_source, utm_medium, utm_campaign, COUNT(*) as cnt FROM site_visits "
            "WHERE created_at >= ? AND (utm_source != '' OR utm_campaign != '') "
            "GROUP BY utm_source, utm_medium, utm_campaign ORDER BY cnt DESC LIMIT 20", (cutoff,)
        ).fetchall()

        # 오늘 방문
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM site_visits WHERE DATE(created_at) = ?", (today,)
        ).fetchone()["cnt"]

        return ok(data={
            "total_visits": total,
            "today_visits": today_count,
            "channels": [{"channel": r["channel"], "count": r["cnt"]} for r in channels],
            "keywords": [{"keyword": r["search_keyword"], "count": r["cnt"]} for r in keywords],
            "pages": [{"page": r["landing_page"], "count": r["cnt"]} for r in pages],
            "daily": [{"date": r["day"], "count": r["cnt"]} for r in daily],
            "campaigns": [
                {"source": r["utm_source"], "medium": r["utm_medium"],
                 "campaign": r["utm_campaign"], "count": r["cnt"]}
                for r in campaigns
            ],
        })
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# TESTIMONIALS API
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/testimonials", tags=["testimonials"])
async def testimonials_list(
    limit: int = 20,
    offset: int = 0,
    random: int = 0,
):
    """공개 리뷰 목록. random=1이면 랜덤 순서."""
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM testimonials WHERE is_visible=1 AND is_deleted=0"
        ).fetchone()[0]
        order = "RANDOM()" if random else "sort_order DESC, id DESC"
        rows = conn.execute(
            f"SELECT id, name, country, photo_url, rating, review_text, sort_order, created_at FROM testimonials WHERE is_visible=1 AND is_deleted=0 ORDER BY {order} LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return ok(data={"total": total, "testimonials": [dict(r) for r in rows]})
    finally:
        conn.close()


@app.post("/api/testimonials", status_code=201, tags=["testimonials"])
async def testimonials_create(request: Request):
    """새 리뷰 추가 (Admin)."""
    _check_admin(request)
    body = await request.json()
    name = (body.get("name") or "").strip()
    country = (body.get("country") or "").strip()
    review_text = (body.get("review_text") or "").strip()
    if not name or not review_text:
        err("name and review_text are required", 400)
    rating = int(body.get("rating", 5))
    photo_url = body.get("photo_url") or None
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        cur = conn.execute(
            "INSERT INTO testimonials (name,country,photo_url,rating,review_text,sort_order,is_visible,is_deleted,created_at,updated_at) VALUES (?,?,?,?,?,0,1,0,?,?)",
            (name, country, photo_url, rating, review_text, now, now),
        )
        conn.commit()
        return ok(data={"id": cur.lastrowid}, message="Testimonial created")
    finally:
        conn.close()


@app.put("/api/testimonials/{tid}", tags=["testimonials"])
async def testimonials_update(tid: int, request: Request):
    """리뷰 수정 (Admin)."""
    _check_admin(request)
    body = await request.json()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    fields = []
    values = []
    for key in ("name", "country", "photo_url", "rating", "review_text", "is_visible"):
        if key in body:
            fields.append(f"{key}=?")
            values.append(body[key])
    if not fields:
        err("No fields to update", 400)
    fields.append("updated_at=?")
    values.append(now)
    values.append(tid)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        conn.execute(f"UPDATE testimonials SET {','.join(fields)} WHERE id=? AND is_deleted=0", values)
        conn.commit()
        return ok(message="Testimonial updated")
    finally:
        conn.close()


@app.delete("/api/testimonials/{tid}", tags=["testimonials"])
async def testimonials_delete(tid: int, request: Request):
    """리뷰 soft-delete (Admin)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        conn.execute("UPDATE testimonials SET is_deleted=1 WHERE id=?", (tid,))
        conn.commit()
        return ok(message="Testimonial deleted")
    finally:
        conn.close()


@app.patch("/api/testimonials/reorder", tags=["testimonials"])
async def testimonials_reorder(request: Request):
    """리뷰 순서 변경 (Admin)."""
    _check_admin(request)
    body = await request.json()
    items = body.get("items", [])
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        for item in items:
            conn.execute("UPDATE testimonials SET sort_order=? WHERE id=?", (item["sort_order"], item["id"]))
        conn.commit()
        return ok(message="Reorder saved")
    finally:
        conn.close()


# ── Secure Download Links System ──────────────────────────────────────────────

_DOWNLOAD_DIR = Path(os.getenv("BRIDGE_DOWNLOAD_DIR", str(Path(__file__).resolve().parent / "secure_downloads")))
_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_download_links_schema():
    """secure download_links + mail_logs 테이블 생성."""
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS download_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            file_path TEXT NOT NULL,
            original_name TEXT NOT NULL,
            candidate_id TEXT,
            max_downloads INTEGER DEFAULT 3,
            download_count INTEGER DEFAULT 0,
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            is_deleted INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS download_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_uuid TEXT NOT NULL,
            ip_hash TEXT,
            downloaded_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mail_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_type TEXT DEFAULT 'profile_broadcast',
            candidate_id TEXT,
            employer_count INTEGER DEFAULT 0,
            sent_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'completed',
            sent_at TEXT DEFAULT (datetime('now')),
            details TEXT
        )
    """)
    conn.commit()
    conn.close()


_ensure_download_links_schema()


@app.post("/api/admin/download-links", tags=["admin"])
async def admin_create_download_link(request: Request):
    """SECURITY: 보안 다운로드 링크 생성 (UUID, 3회 제한, 14일 만료)."""
    _check_admin(request)
    body = await request.json()
    file_path = body.get("file_path", "")
    original_name = body.get("original_name", "")
    candidate_id = body.get("candidate_id", "")

    if not file_path or not original_name:
        raise HTTPException(400, "file_path and original_name required")

    # SECURITY: 첨부파일명에 실명 금지 → candidate_{번호}_resume.pdf
    if candidate_id:
        ext = Path(original_name).suffix
        original_name = f"candidate_{candidate_id}{ext}"

    link_uuid = str(uuid.uuid4())
    expires = (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        conn.execute(
            """INSERT INTO download_links (uuid, file_path, original_name, candidate_id, max_downloads, expires_at)
               VALUES (?, ?, ?, ?, 3, ?)""",
            (link_uuid, file_path, original_name, candidate_id, expires),
        )
        conn.commit()
    finally:
        conn.close()

    return ok(data={"uuid": link_uuid, "url": f"/dl/{link_uuid}", "expires_at": expires})


@app.get("/dl/{link_uuid}", tags=["download"])
async def download_file(link_uuid: str, request: Request):
    """SECURITY: 보안 파일 다운로드 — UUID 기반, 횟수/만료 제한."""
    from fastapi.responses import FileResponse as FastFileResponse

    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        link = conn.execute(
            "SELECT * FROM download_links WHERE uuid = ? AND is_deleted = 0", (link_uuid,)
        ).fetchone()

        if not link:
            return SafeJSONResponse({"error": "링크를 찾을 수 없습니다"}, status_code=404)

        # SECURITY: 다운로드 횟수 제한 (최대 3회)
        if link["download_count"] >= link["max_downloads"]:
            return SafeJSONResponse(
                {"error": "다운로드 횟수를 초과했습니다 (최대 3회)"}, status_code=403
            )

        # SECURITY: 만료일 체크 (14일)
        expires = datetime.strptime(link["expires_at"], "%Y-%m-%d %H:%M:%S")
        if datetime.now(timezone.utc).replace(tzinfo=None) > expires:
            return SafeJSONResponse(
                {"error": "링크가 만료되었습니다 (14일)"}, status_code=410
            )

        file_p = Path(link["file_path"])
        if not file_p.exists():
            return SafeJSONResponse({"error": "파일을 찾을 수 없습니다"}, status_code=404)

        # SECURITY: 다운로드 카운트 증가 + IP 로그
        ip_h = _ip_hash(request)
        conn.execute(
            "UPDATE download_links SET download_count = download_count + 1 WHERE uuid = ?",
            (link_uuid,),
        )
        conn.execute(
            "INSERT INTO download_logs (link_uuid, ip_hash) VALUES (?, ?)",
            (link_uuid, ip_h),
        )
        conn.commit()

        return FastFileResponse(
            path=str(file_p),
            filename=link["original_name"],
            media_type="application/octet-stream",
        )
    finally:
        conn.close()


@app.post("/api/admin/download-links/cleanup", tags=["admin"])
async def admin_cleanup_download_links(request: Request):
    """SECURITY: 만료된 다운로드 링크 + 파일 자동 삭제."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        expired = conn.execute(
            "SELECT uuid, file_path FROM download_links WHERE expires_at < ? AND is_deleted = 0",
            (now_str,),
        ).fetchall()

        cleaned = 0
        for row in expired:
            fp = Path(row["file_path"])
            if fp.exists():
                fp.unlink()
            conn.execute(
                "UPDATE download_links SET is_deleted = 1 WHERE uuid = ?", (row["uuid"],)
            )
            cleaned += 1

        conn.commit()
        return ok(message=f"만료 링크 {cleaned}건 정리 완료")
    finally:
        conn.close()


# ── Secure Profile Broadcast (보안 규칙 적용) ────────────────────────────────


class SecureProfileBroadcastBody(BaseModel):
    candidate_id: str
    employer_ids: list[int]
    custom_subject: Optional[str] = None
    custom_body: Optional[str] = None
    download_link_uuid: Optional[str] = None


@app.post("/api/admin/matching/send-profile-secure", tags=["admin"])
async def admin_matching_send_profile_secure(request: Request, body: SecureProfileBroadcastBody):
    """SECURITY: 매칭된 employer들에게 후보자 프로필 개별 발송 (전체 보안 규칙 적용).

    보안 규칙:
    1. 완전 개별 발송 — CC/BCC 절대 금지, To에 1명만
    2. PII 마스킹 — 후보자 실명/이메일/전화/주소 절대 미포함
    3. Reply-To: bridgejobkr@gmail.com (회신 격리)
    4. 발송 전 PII 자동 스캔
    5. Rate limit: 3초 간격, 10/분, 200/일
    6. 발송 로그: employer 이메일 마스킹 저장
    """
    _check_admin(request)
    if not body.employer_ids:
        raise HTTPException(400, "employer_ids가 비어 있습니다.")

    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        # 후보자 조회
        cand = conn.execute(
            "SELECT * FROM candidates WHERE candidate_id = ?", (body.candidate_id,)
        ).fetchone()
        if not cand:
            raise HTTPException(404, "Candidate not found")
        cand_d = dict(cand)

        # SECURITY: 프로필 카드 — PII 제외
        card_html = _build_profile_card(cand_d)

        # 템플릿 로드
        tpl = conn.execute(
            "SELECT subject, body_html FROM email_templates WHERE template_key = 'profile_broadcast'"
        ).fetchone()
        if not tpl:
            raise HTTPException(404, "profile_broadcast template not found")

        base_subject = body.custom_subject or tpl["subject"]
        base_body = body.custom_body or tpl["body_html"]

        # 다운로드 링크 삽입
        dl_html = ""
        if body.download_link_uuid:
            dl_html = f'<p style="margin:16px 0"><a href="https://bridgejob.co.kr/dl/{body.download_link_uuid}" style="display:inline-block;background:#1d1d1f;color:#fff;padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:600">View Full Profile</a></p>'

        sent_count = 0
        fail_count = 0
        results = []

        for emp_id in body.employer_ids:
            emp = conn.execute(
                "SELECT id, email, school_name, contact_name FROM client_inquiries WHERE id = ?",
                (emp_id,),
            ).fetchone()
            if not emp or not emp["email"]:
                continue

            school = emp["school_name"] or "School"
            to_email = emp["email"]

            # 개별 템플릿 치환
            html = base_body.replace("{{profile_cards}}", card_html)
            html = html.replace("{{school_name}}", school)
            html = html.replace("{{contact_name}}", emp["contact_name"] or "")
            html = html.replace("{{download_link}}", dl_html)
            html = re.sub(r"\{\{\w+\}\}", "", html)

            subject = f"{base_subject} - {school}" if school != "School" else base_subject

            # SECURITY: 개별 발송 + PII 스캔 + Rate limit
            success, msg = _secure_send_email(to_email, subject, html)

            status_val = "sent" if success else "failed"
            if success:
                sent_count += 1
            else:
                fail_count += 1

            # SECURITY: 발송 로그 — 이메일 마스킹 저장
            conn.execute(
                """INSERT INTO profile_sends (candidate_id, employer_id, school_name, to_email, status)
                   VALUES (?, ?, ?, ?, ?)""",
                (body.candidate_id, emp_id, school, _mask_email_for_log(to_email), status_val),
            )
            results.append({"employer_id": emp_id, "school": school, "status": status_val, "message": msg})

            # SECURITY: 발송 간격 최소 3초
            if success:
                await asyncio.sleep(3)

        conn.commit()

        # SECURITY: 메일 발송 로그 (수신자 이메일 직접 저장 금지)
        conn.execute(
            """INSERT INTO mail_logs (log_type, candidate_id, employer_count, sent_count, failed_count, status, details)
               VALUES ('profile_broadcast', ?, ?, ?, ?, 'completed', ?)""",
            (body.candidate_id, len(body.employer_ids), sent_count, fail_count,
             json.dumps({"employer_ids": body.employer_ids})),
        )
        conn.commit()

        return ok(
            message=f"Profile broadcast: {sent_count} sent, {fail_count} failed",
            data={"sent": sent_count, "failed": fail_count, "results": results},
        )
    finally:
        conn.close()


@app.get("/api/admin/mail-logs", tags=["admin"])
async def admin_mail_logs(request: Request, log_type: str = "", limit: int = 100):
    """SECURITY: 메일 발송 로그 조회 (수신자 이메일 직접 저장 없음)."""
    _check_admin(request)
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        if log_type:
            rows = conn.execute(
                "SELECT * FROM mail_logs WHERE log_type = ? ORDER BY sent_at DESC LIMIT ?",
                (log_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM mail_logs ORDER BY sent_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return ok(data=[dict(r) for r in rows])
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

