"""
BRIDGE 입력 검증 모듈
- InputSanitizer: SQL Injection, XSS, Prompt Injection 방어

관리자 인증: api_server.py _check_admin() (ADMIN_API_KEY 기반)
Rate Limit: api_server.py _rate_ok() + _mail_rate_check()
"""

from __future__ import annotations

import re
import logging

log = logging.getLogger("bridge.security.auth")


class InputSanitizer:
    """입력값 검증 — SQL Injection, Prompt Injection 방어"""

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
        result = text.replace("<", "&lt;").replace(">", "&gt;")
        result = result.replace("'", "&#39;").replace('"', "&quot;")
        return result
