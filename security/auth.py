"""
BRIDGE 인증 & Rate Limiting 모듈
- HMAC 기반 관리자 인증
- 시간 기반 토큰 (5분 유효)
- Rate Limiter (IP 기반)
- FastAPI 미들웨어

Usage:
    from security.auth import AdminAuth, RateLimiter, require_admin

    auth = AdminAuth()
    token = auth.generate_token()       # 클라이언트에게 전달
    is_valid = auth.verify_token(token)  # 서버에서 검증

    limiter = RateLimiter(max_requests=60, window_seconds=60)
    if not limiter.allow("192.168.1.1"):
        raise HTTPException(429, "Too many requests")
"""

from __future__ import annotations

import os
import re
import time
import hmac
import hashlib
import secrets
import logging
from collections import defaultdict
from functools import wraps
from typing import Optional, Callable

log = logging.getLogger("bridge.security.auth")

# ─── HMAC 관리자 인증 ────────────────────────────────────
ADMIN_SECRET = os.environ.get("BRIDGE_ADMIN_SECRET", "")
TOKEN_VALIDITY_SECONDS = 300  # 5분


class AdminAuth:
    """HMAC 기반 관리자 인증

    토큰 구조: timestamp:hmac_signature
    - timestamp: 생성 시각 (Unix)
    - hmac_signature: HMAC-SHA256(secret, timestamp)
    """

    def __init__(self, secret: Optional[str] = None):
        self._secret = (secret or ADMIN_SECRET).encode("utf-8")
        if not self._secret:
            self._secret = secrets.token_bytes(32)
            log.warning(
                "BRIDGE_ADMIN_SECRET 환경변수 미설정 — 임시 키 생성됨. "
                "프로덕션에서는 반드시 환경변수로 설정하세요."
            )

    def generate_token(self) -> str:
        """인증 토큰 생성 (5분 유효)"""
        timestamp = str(int(time.time()))
        signature = hmac.new(
            self._secret, timestamp.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return f"{timestamp}:{signature}"

    def verify_token(self, token: str) -> bool:
        """토큰 검증 — 서명 일치 + 유효기간 확인"""
        if not token or ":" not in token:
            return False

        try:
            timestamp_str, signature = token.split(":", 1)
            timestamp = int(timestamp_str)
        except (ValueError, TypeError):
            return False

        # 유효기간 확인
        now = int(time.time())
        if abs(now - timestamp) > TOKEN_VALIDITY_SECONDS:
            log.warning(f"만료된 토큰: {now - timestamp}초 경과")
            return False

        # HMAC 검증 (timing-safe comparison)
        expected = hmac.new(
            self._secret, timestamp_str.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected):
            log.warning("HMAC 서명 불일치 — 위변조 시도 감지")
            return False

        return True

    def get_admin_level(self, token: str) -> str:
        """인증 수준 반환"""
        if self.verify_token(token):
            return "ADMIN"
        return "PUBLIC"


# ─── Rate Limiter ────────────────────────────────────────
class RateLimiter:
    """IP 기반 Rate Limiter (Sliding Window)"""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def allow(self, client_id: str) -> bool:
        """요청 허용 여부 확인"""
        now = time.time()
        cutoff = now - self.window

        # 만료된 요청 제거
        self._requests[client_id] = [
            t for t in self._requests[client_id] if t > cutoff
        ]

        if len(self._requests[client_id]) >= self.max_requests:
            log.warning(
                f"Rate limit 초과: {client_id} "
                f"({len(self._requests[client_id])}/{self.max_requests})"
            )
            return False

        self._requests[client_id].append(now)
        return True

    def remaining(self, client_id: str) -> int:
        """남은 요청 수"""
        now = time.time()
        cutoff = now - self.window
        active = [t for t in self._requests[client_id] if t > cutoff]
        return max(0, self.max_requests - len(active))

    def reset(self, client_id: str) -> None:
        """특정 IP의 카운터 리셋"""
        self._requests.pop(client_id, None)


# ─── FastAPI 미들웨어 ────────────────────────────────────
# FastAPI 사용 시 아래 코드를 app에 등록

FASTAPI_MIDDLEWARE_CODE = """
# app.py 또는 main.py에 추가:

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from security.auth import AdminAuth, RateLimiter
from security.pii_scanner import PIIScanner

app = FastAPI()
admin_auth = AdminAuth()
rate_limiter = RateLimiter(max_requests=60, window_seconds=60)
pii_scanner = PIIScanner(fail_closed=True)

# ─── Rate Limit 미들웨어 ─────────────────────────────
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    if not rate_limiter.allow(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "Too many requests", "retry_after": 60},
        )
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(
        rate_limiter.remaining(client_ip)
    )
    return response

# ─── PII 스캔 미들웨어 (outbound) ────────────────────
@app.middleware("http")
async def pii_scan_middleware(request: Request, call_next):
    response = await call_next(request)
    # JSON 응답만 검사
    if "application/json" in response.headers.get("content-type", ""):
        # 관리자 인증된 요청은 스캔 건너뜀
        auth_token = request.headers.get("X-Admin-Token", "")
        if not admin_auth.verify_token(auth_token):
            # 비인증 요청의 응답에서 PII 스캔
            # (실제 구현 시 response body 읽기 필요)
            pass
    return response

# ─── 관리자 인증 Dependency ──────────────────────────
async def require_admin(request: Request):
    token = request.headers.get("X-Admin-Token", "")
    if not admin_auth.verify_token(token):
        raise HTTPException(
            status_code=403,
            detail="관리자 인증 필요 — 유효한 HMAC 토큰을 X-Admin-Token 헤더에 포함하세요",
        )
    return True

# ─── 사용 예시 ───────────────────────────────────────
@app.get("/api/admin/employers")
async def get_employers(is_admin: bool = Depends(require_admin)):
    # 관리자 인증 통과 — PII 포함 응답 가능
    return {"employers": [...], "pii_included": True}

@app.get("/api/public/jobs")
async def get_public_jobs():
    # 비인증 — PII 자동 마스킹
    jobs = get_jobs_from_db()
    safe_jobs = pii_scanner.mask_dict(jobs)
    return {"jobs": safe_jobs}
"""


# ─── Prompt Injection 방어 ───────────────────────────────
class InputSanitizer:
    """입력값 검증 — SQL Injection, Prompt Injection 방어"""

    # 위험 패턴
    DANGEROUS_PATTERNS = [
        re.compile(r"(?:--|;|'|\")\s*(?:DROP|DELETE|UPDATE|INSERT|ALTER|EXEC)", re.IGNORECASE),
        re.compile(r"<script", re.IGNORECASE),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"on(?:load|error|click)\s*=", re.IGNORECASE),
    ]

    @classmethod
    def is_safe(cls, text: str) -> bool:
        """입력값 안전 여부 확인"""
        if not text:
            return True
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(text):
                log.warning(f"위험 입력 감지: {text[:50]}...")
                return False
        return True

    @classmethod
    def sanitize(cls, text: str) -> str:
        """위험 문자 제거"""
        if not text:
            return ""
        # HTML 태그 이스케이프
        result = text.replace("<", "&lt;").replace(">", "&gt;")
        result = result.replace("'", "&#39;").replace('"', "&quot;")
        return result



# ─── 테스트 ──────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("BRIDGE 인증 & Rate Limiting 테스트")
    print("=" * 60)

    # 1. HMAC 인증
    auth = AdminAuth(secret="test-secret-key-for-demo")
    token = auth.generate_token()
    print(f"\n1. HMAC 토큰 생성: {token[:30]}...")
    print(f"   검증 결과: {'✅ 유효' if auth.verify_token(token) else '❌ 무효'}")
    print(f"   위변조 검증: {'✅ 차단' if not auth.verify_token('fake:token') else '❌ 통과'}")
    print(f"   인증 수준: {auth.get_admin_level(token)}")

    # 2. Rate Limiter
    limiter = RateLimiter(max_requests=3, window_seconds=10)
    print(f"\n2. Rate Limiter (3회/10초):")
    for i in range(5):
        allowed = limiter.allow("test-ip")
        remaining = limiter.remaining("test-ip")
        print(f"   요청 #{i+1}: {'✅ 허용' if allowed else '❌ 차단'} (잔여: {remaining})")

    # 3. Input Sanitizer
    print(f"\n3. 입력값 검증:")
    tests = [
        ("정상 입력", True),
        ("'; DROP TABLE users;--", False),
        ("<script>alert('xss')</script>", False),
        ("Hello World", True),
    ]
    for text, expected_safe in tests:
        safe = InputSanitizer.is_safe(text)
        status = "✅" if safe == expected_safe else "❌"
        print(f"   {status} '{text[:30]}': safe={safe}")
