"""
security_middleware.py — BRIDGE 보안 미들웨어

기능:
1. 감사 로그 (audit/audit_YYYY-MM-DD.jsonl)
2. 보안 헤더
3. Rate Limiting 강화

api_server.py에서 import:
    from security_middleware import SecurityMiddleware
    app.add_middleware(SecurityMiddleware)
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response, JSONResponse
except ImportError:
    raise ImportError("starlette 필요: pip install starlette")


# ── 설정 ──────────────────────────────────────────────────────────────────────

AUDIT_DIR = Path(os.getenv("AUDIT_DIR", str(Path(__file__).resolve().parent / "audit")))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))     # 초
RATE_LIMIT_MAX    = int(os.getenv("RATE_LIMIT_MAX", "120"))        # 윈도우당 최대 요청
RATE_LIMIT_ADMIN  = int(os.getenv("RATE_LIMIT_ADMIN_MAX", "300"))  # admin은 더 관대

# 보안 헤더
SECURITY_HEADERS = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
}

# Rate limit 저장소
_rate_store: dict[str, list[float]] = defaultdict(list)


def _client_ip(request: Request) -> str:
    """클라이언트 IP 추출 (프록시 지원)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _is_admin_request(request: Request) -> bool:
    """admin API 요청 여부."""
    return request.url.path.startswith("/api/admin")


def _check_rate_limit(ip: str, is_admin: bool) -> bool:
    """글로벌 Rate limit 체크. True = 허용, False = 차단."""
    now = time.time()
    max_reqs = RATE_LIMIT_ADMIN if is_admin else RATE_LIMIT_MAX

    # 윈도우 밖의 오래된 요청 제거
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < RATE_LIMIT_WINDOW]

    if len(_rate_store[ip]) >= max_reqs:
        return False

    _rate_store[ip].append(now)
    return True


# ── 엔드포인트별 Rate Limit ──────────────────────────────────────────────────
# key=(ip, endpoint_group) → [timestamps]
_endpoint_rate_store: dict[tuple[str, str], list[float]] = defaultdict(list)

# 엔드포인트 그룹별 제한 (window_sec, max_requests)
_ENDPOINT_LIMITS: dict[str, tuple[int, int]] = {
    "apply":     (3600, 10),   # 10/hr
    "inquiry":   (3600, 5),    # 5/hr
    "community": (300, 5),     # 5/5min
}

# Admin 로그인 실패 잠금: ip → [fail_timestamps]
_admin_fail_store: dict[str, list[float]] = defaultdict(list)
_ADMIN_FAIL_MAX = 5           # 최대 실패 횟수
_ADMIN_LOCK_WINDOW = 900      # 15분 잠금


def _get_endpoint_group(path: str, method: str) -> str | None:
    """요청 경로를 엔드포인트 그룹으로 매핑."""
    if path == "/api/apply" and method == "POST":
        return "apply"
    if path == "/api/inquiry" and method == "POST":
        return "inquiry"
    if path.startswith("/api/community/") and method == "POST":
        return "community"
    return None


def _check_endpoint_limit(ip: str, path: str, method: str) -> bool:
    """엔드포인트별 rate limit. True = 허용."""
    group = _get_endpoint_group(path, method)
    if not group:
        return True

    window, max_reqs = _ENDPOINT_LIMITS[group]
    now = time.time()
    key = (ip, group)
    _endpoint_rate_store[key] = [t for t in _endpoint_rate_store[key] if now - t < window]

    if len(_endpoint_rate_store[key]) >= max_reqs:
        return False

    _endpoint_rate_store[key].append(now)
    return True


def _check_admin_lockout(ip: str) -> bool:
    """Admin 인증 실패 잠금 체크. True = 허용 (잠금 아님)."""
    now = time.time()
    _admin_fail_store[ip] = [t for t in _admin_fail_store[ip] if now - t < _ADMIN_LOCK_WINDOW]
    return len(_admin_fail_store[ip]) < _ADMIN_FAIL_MAX


def _record_admin_fail(ip: str):
    """Admin 인증 실패 기록."""
    _admin_fail_store[ip].append(time.time())


def _write_audit_log(
    request: Request,
    status_code: int,
    duration_ms: float,
    ip: str,
):
    """감사 로그를 JSONL 파일에 기록."""
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = AUDIT_DIR / f"audit_{today}.jsonl"

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "method": request.method,
        "path": request.url.path,
        "ip": ip,
        "status": status_code,
        "duration_ms": round(duration_ms, 1),
        "user_agent": (request.headers.get("user-agent") or "")[:200],
    }

    # admin 요청은 admin key 존재 여부 기록 (키 자체는 기록하지 않음)
    if _is_admin_request(request):
        entry["admin_auth"] = bool(request.headers.get("x-admin-key"))

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 로그 실패로 서비스 중단하지 않음


_IS_PROD = os.getenv("BRIDGE_ENV", os.getenv("ENV", "")).lower() in ("production", "prod")


class SecurityMiddleware(BaseHTTPMiddleware):
    """BRIDGE 보안 미들웨어: 헤더 + Rate Limit + 감사 로그 + 스택 트레이스 억제."""

    async def dispatch(self, request: Request, call_next):
        ip = _client_ip(request)
        is_admin = _is_admin_request(request)

        # ── Admin 로그인 잠금 체크 ──
        if is_admin and not _check_admin_lockout(ip):
            _write_audit_log(request, 423, 0, ip)
            return JSONResponse(
                {"detail": "인증 실패가 반복되어 15분간 접근이 제한됩니다."},
                status_code=423,
                headers=SECURITY_HEADERS,
            )

        # ── 글로벌 Rate Limit ──
        if not _check_rate_limit(ip, is_admin):
            _write_audit_log(request, 429, 0, ip)
            return JSONResponse(
                {"detail": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."},
                status_code=429,
                headers=SECURITY_HEADERS,
            )

        # ── 엔드포인트별 Rate Limit ──
        if not _check_endpoint_limit(ip, request.url.path, request.method):
            _write_audit_log(request, 429, 0, ip)
            return JSONResponse(
                {"detail": "이 기능의 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요."},
                status_code=429,
                headers=SECURITY_HEADERS,
            )

        # ── 요청 처리 ──
        start = time.time()
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            # 프로덕션: 스택 트레이스 억제, 안전한 에러 메시지 반환
            duration_ms = (time.time() - start) * 1000
            _write_audit_log(request, 500, duration_ms, ip)
            if _IS_PROD:
                return JSONResponse(
                    {"detail": "서버 내부 오류가 발생했습니다."},
                    status_code=500,
                    headers=SECURITY_HEADERS,
                )
            raise

        duration_ms = (time.time() - start) * 1000

        # ── Admin 인증 실패 기록 ──
        if is_admin and response.status_code == 403:
            _record_admin_fail(ip)

        # ── 보안 헤더 ──
        for key, value in SECURITY_HEADERS.items():
            response.headers[key] = value

        # ── 감사 로그 (API 요청만) ──
        if request.url.path.startswith("/api/"):
            _write_audit_log(request, response.status_code, duration_ms, ip)

        return response
