"""
BRIDGE Security Package
- pii_scanner: outbound PII 감지 + fail-closed 차단
- auth: InputSanitizer (XSS/SQL Injection 방지)

암호화는 security_vault.py 단일 모듈 사용 (BRIDGE_FIELD_KEY 환경변수).
PIICrypto / AdminAuth / RateLimiter 는 기존 api_server.py 구현으로 통합됨.
"""

from security.pii_scanner import PIIScanner
from security.auth import InputSanitizer

__all__ = [
    "PIIScanner",
    "InputSanitizer",
]
