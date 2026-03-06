"""
security/auth.py — BRIDGE Authentication, Rate Limiting, Input Sanitization
=============================================================================
AdminAuth:    HMAC-SHA256 토큰 인증 (5분 유효, timing-safe 비교)
RateLimiter:  IP 기반 Sliding Window (기본 60회/분)
InputSanitizer: SQL Injection + XSS 방어
"""

import hashlib
import hmac
import html
import os
import re
import time
from collections import defaultdict
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# AdminAuth — HMAC-SHA256 토큰 인증
# ═══════════════════════════════════════════════════════════════

class AdminAuth:
    """
    HMAC-SHA256 기반 관리자 인증.
    토큰 형식: "timestamp:signature"
    유효기간: 5분 (300초)
    """

    def __init__(self, secret: Optional[str] = None, max_age: int = 300):
        self._secret = (
            secret
            or os.getenv("BRIDGE_ADMIN_SECRET", "").strip()
            or os.getenv("ADMIN_API_KEY", "").strip()
        )
        if not self._secret:
            raise EnvironmentError(
                "BRIDGE_ADMIN_SECRET (or ADMIN_API_KEY) is not set. "
                "Check your .env file."
            )
        self._max_age = max_age

    def generate_token(self) -> str:
        """
        새 인증 토큰 생성.
        Returns: "timestamp:signature"
        """
        ts = str(int(time.time()))
        sig = hmac.new(
            self._secret.encode("utf-8"),
            ts.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"{ts}:{sig}"

    def verify_token(self, token: str) -> bool:
        """
        토큰 검증. timing-safe 비교 사용.
        Returns: True if valid and not expired.
        """
        if not token or ":" not in token:
            return False

        parts = token.split(":", 1)
        if len(parts) != 2:
            return False

        ts_str, provided_sig = parts

        # 타임스탬프 유효성
        try:
            ts = int(ts_str)
        except (ValueError, TypeError):
            return False

        # 만료 확인
        if abs(time.time() - ts) > self._max_age:
            return False

        # HMAC 재계산 + timing-safe 비교
        expected_sig = hmac.new(
            self._secret.encode("utf-8"),
            ts_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_sig, provided_sig)


# ═══════════════════════════════════════════════════════════════
# RateLimiter — IP 기반 Sliding Window
# ═══════════════════════════════════════════════════════════════

class RateLimiter:
    """
    IP 기반 슬라이딩 윈도우 Rate Limiter.
    기본: 60회/분
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self._max_requests = max_requests
        self._window = window_seconds
        self._windows: dict[str, list[float]] = defaultdict(list)

    def allow(self, client_id: str) -> bool:
        """
        요청 허용 여부 확인.
        Returns: True = 허용, False = 차단
        """
        now = time.time()
        cutoff = now - self._window

        # 만료된 타임스탬프 제거
        timestamps = self._windows[client_id]
        self._windows[client_id] = [t for t in timestamps if t > cutoff]

        if len(self._windows[client_id]) >= self._max_requests:
            return False

        self._windows[client_id].append(now)
        return True

    def reset(self, client_id: str):
        """특정 클라이언트 카운터 리셋."""
        self._windows.pop(client_id, None)

    def get_remaining(self, client_id: str) -> int:
        """남은 요청 수."""
        now = time.time()
        cutoff = now - self._window
        active = [t for t in self._windows.get(client_id, []) if t > cutoff]
        return max(0, self._max_requests - len(active))


# ═══════════════════════════════════════════════════════════════
# InputSanitizer — SQL Injection + XSS 방어
# ═══════════════════════════════════════════════════════════════

# SQL Injection 패턴
_SQL_PATTERNS = [
    re.compile(
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|EXEC|EXECUTE|"
        r"TRUNCATE|CREATE|REPLACE|MERGE)\b\s)",
        re.IGNORECASE,
    ),
    re.compile(r"(--|;|\/\*|\*\/|@@|char\(|nchar\()", re.IGNORECASE),
    re.compile(r"(\bOR\b\s+\d+\s*=\s*\d+|\bAND\b\s+\d+\s*=\s*\d+)", re.IGNORECASE),
    re.compile(r"(sleep\(|benchmark\(|waitfor\s+delay|load_file|into\s+outfile)", re.IGNORECASE),
    re.compile(r"(0x[0-9a-fA-F]+)", re.IGNORECASE),
]

# XSS 패턴
_XSS_PATTERNS = [
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"on\w+\s*=\s*['\"]", re.IGNORECASE),
    re.compile(r"<\s*iframe", re.IGNORECASE),
    re.compile(r"<\s*object", re.IGNORECASE),
    re.compile(r"<\s*embed", re.IGNORECASE),
    re.compile(r"expression\s*\(", re.IGNORECASE),
    re.compile(r"vbscript\s*:", re.IGNORECASE),
    re.compile(r"data\s*:\s*text/html", re.IGNORECASE),
]


class InputSanitizer:
    """SQL Injection + XSS 방어."""

    @staticmethod
    def is_safe(text: str) -> bool:
        """
        입력값 안전 여부 확인.
        Returns: True = 안전, False = 위험 패턴 감지
        """
        if not text or not isinstance(text, str):
            return True

        # SQL Injection 검사
        for pattern in _SQL_PATTERNS:
            if pattern.search(text):
                return False

        # XSS 검사
        for pattern in _XSS_PATTERNS:
            if pattern.search(text):
                return False

        return True

    @staticmethod
    def sanitize(text: str) -> str:
        """
        위험 문자를 이스케이프하여 안전한 문자열 반환.
        HTML 엔티티 변환 + SQL 주석 제거.
        """
        if not text or not isinstance(text, str):
            return text

        # HTML 이스케이프 (XSS 방어)
        result = html.escape(text, quote=True)

        # SQL 주석 제거
        result = re.sub(r"/\*.*?\*/", "", result, flags=re.DOTALL)
        result = re.sub(r"--.*$", "", result, flags=re.MULTILINE)

        # 세미콜론 제거 (SQL 멀티스테이트먼트 방지)
        result = result.replace(";", "")

        return result.strip()

    @staticmethod
    def sanitize_dict(data: dict) -> dict:
        """dict의 모든 문자열 값을 sanitize."""
        if not isinstance(data, dict):
            return data
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = InputSanitizer.sanitize(value)
            elif isinstance(value, dict):
                result[key] = InputSanitizer.sanitize_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    InputSanitizer.sanitize(v) if isinstance(v, str) else v
                    for v in value
                ]
            else:
                result[key] = value
        return result


# ── Self-test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from pathlib import Path as _P
    try:
        from dotenv import load_dotenv
        load_dotenv(_P(__file__).resolve().parent.parent / ".env")
    except ImportError:
        pass

    print("[auth] Self-test start...")
    all_passed = True

    # 1. AdminAuth
    try:
        auth = AdminAuth()
        token = auth.generate_token()
        ok1 = auth.verify_token(token)
        print(f"  [{'PASS' if ok1 else 'FAIL'}] AdminAuth generate+verify: {ok1}")
        if not ok1:
            all_passed = False

        # 만료된 토큰 (임의 과거 타임스탬프)
        old_token = "1000000000:fake_signature"
        ok2 = not auth.verify_token(old_token)
        print(f"  [{'PASS' if ok2 else 'FAIL'}] AdminAuth expired token rejected: {ok2}")
        if not ok2:
            all_passed = False

        # 변조된 토큰
        tampered = token.split(":")[0] + ":tampered_signature"
        ok3 = not auth.verify_token(tampered)
        print(f"  [{'PASS' if ok3 else 'FAIL'}] AdminAuth tampered token rejected: {ok3}")
        if not ok3:
            all_passed = False

    except EnvironmentError as e:
        print(f"  [SKIP] AdminAuth: {e}")

    # 2. RateLimiter
    rl = RateLimiter(max_requests=3, window_seconds=60)
    ok4 = rl.allow("test_ip") and rl.allow("test_ip") and rl.allow("test_ip")
    ok5 = not rl.allow("test_ip")  # 4th should be blocked
    print(f"  [{'PASS' if ok4 else 'FAIL'}] RateLimiter 3 requests allowed: {ok4}")
    print(f"  [{'PASS' if ok5 else 'FAIL'}] RateLimiter 4th blocked: {ok5}")
    if not (ok4 and ok5):
        all_passed = False

    remaining = rl.get_remaining("test_ip")
    ok6 = remaining == 0
    print(f"  [{'PASS' if ok6 else 'FAIL'}] RateLimiter remaining: {remaining}")
    if not ok6:
        all_passed = False

    # 3. InputSanitizer
    san = InputSanitizer()

    ok7 = not san.is_safe("SELECT * FROM users")
    ok8 = not san.is_safe("<script>alert('xss')</script>")
    ok9 = san.is_safe("Hello, world!")
    ok10 = not san.is_safe("1 OR 1=1")
    print(f"  [{'PASS' if ok7 else 'FAIL'}] SQL injection detected: {ok7}")
    print(f"  [{'PASS' if ok8 else 'FAIL'}] XSS detected: {ok8}")
    print(f"  [{'PASS' if ok9 else 'FAIL'}] Clean input safe: {ok9}")
    print(f"  [{'PASS' if ok10 else 'FAIL'}] OR 1=1 detected: {ok10}")
    if not (ok7 and ok8 and ok9 and ok10):
        all_passed = False

    sanitized = san.sanitize("<script>alert('xss')</script>")
    ok11 = "<script>" not in sanitized
    print(f"  [{'PASS' if ok11 else 'FAIL'}] sanitize XSS: {sanitized}")
    if not ok11:
        all_passed = False

    if all_passed:
        print("\n  All auth/rate-limiter/sanitizer tests PASSED.")
    else:
        print("\n  Some tests FAILED.")
