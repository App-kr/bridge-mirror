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
    """Rate limit 체크. True = 허용, False = 차단."""
    now = time.time()
    max_reqs = RATE_LIMIT_ADMIN if is_admin else RATE_LIMIT_MAX

    # 윈도우 밖의 오래된 요청 제거
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < RATE_LIMIT_WINDOW]

    if len(_rate_store[ip]) >= max_reqs:
        return False

    _rate_store[ip].append(now)
    return True


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


class SecurityMiddleware(BaseHTTPMiddleware):
    """BRIDGE 보안 미들웨어: 헤더 + Rate Limit + 감사 로그."""

    async def dispatch(self, request: Request, call_next):
        ip = _client_ip(request)
        is_admin = _is_admin_request(request)

        # ── Rate Limit ──
        if not _check_rate_limit(ip, is_admin):
            _write_audit_log(request, 429, 0, ip)
            return JSONResponse(
                {"detail": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."},
                status_code=429,
                headers=SECURITY_HEADERS,
            )

        # ── 요청 처리 ──
        start = time.time()
        response: Response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        # ── 보안 헤더 ──
        for key, value in SECURITY_HEADERS.items():
            response.headers[key] = value

        # ── 감사 로그 (API 요청만) ──
        if request.url.path.startswith("/api/"):
            _write_audit_log(request, response.status_code, duration_ms, ip)

        return response
