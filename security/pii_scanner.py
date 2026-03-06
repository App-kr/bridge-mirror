"""
BRIDGE PII 스캐너
- 모든 outbound 데이터(API 응답, 메일, 로그)에서 PII 감지
- Fail-Closed: PII 감지되면 차단 (통과시키지 않음)
- 자동 마스킹 옵션

Usage:
    from security.pii_scanner import PIIScanner

    scanner = PIIScanner()
    
    # API 응답 검사
    result = scanner.scan(api_response_dict)
    if result.has_pii:
        blocked_response = scanner.mask_all(api_response_dict)
    
    # 문자열 검사
    if scanner.contains_pii("이메일은 test@gmail.com입니다"):
        print("PII 감지!")
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger("bridge.security.pii")


# ─── PII 패턴 정의 ──────────────────────────────────────
PII_PATTERNS = {
    "phone_kr": {
        "pattern": re.compile(
            r"(?:010|011|016|017|018|019|02|031|032|033|041|042|043|044|051|052|053|054|055|061|062|063|064|070)"
            r"[-.\s]?\d{3,4}[-.\s]?\d{4}"
        ),
        "level": "CRITICAL",
        "description": "한국 전화번호",
    },
    "email": {
        "pattern": re.compile(
            r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
        ),
        "level": "CRITICAL",
        "description": "이메일 주소",
    },
    "korean_name_with_title": {
        "pattern": re.compile(
            r"(?:원장|부장|대표|사장|팀장|실장|과장|부원장|이사)"
            r"\s*[가-힣]{2,4}"
        ),
        "level": "CRITICAL",
        "description": "직함+한글이름",
    },
    "kakao_id": {
        "pattern": re.compile(
            r"(?:카카오|카톡|kakao|katalk)\s*(?:ID|아이디)?\s*[:=]?\s*([a-zA-Z0-9_.]{3,20})",
            re.IGNORECASE,
        ),
        "level": "CRITICAL",
        "description": "카카오톡 ID",
    },
    "passport": {
        "pattern": re.compile(r"[A-Z]{1,2}\d{7,8}"),
        "level": "CRITICAL",
        "description": "여권번호 패턴",
    },
    "alien_registration": {
        "pattern": re.compile(r"\d{6}[-\s]?\d{7}"),
        "level": "CRITICAL",
        "description": "외국인등록번호 패턴",
    },
}

# 화이트리스트 — PII로 오탐하지 않을 패턴
WHITELIST_PATTERNS = [
    re.compile(r"bridgejob\.co\.kr"),
    re.compile(r"bridgejobkr@(?:gmail|naver)\.com"),  # 발신자 주소
    re.compile(r"Job\.\s*\d+"),  # Job 번호
    re.compile(r"\d{4}[-/]\d{2}[-/]\d{2}"),  # 날짜
]


@dataclass
class PIIScanResult:
    """PII 스캔 결과"""
    has_pii: bool = False
    findings: list[dict] = field(default_factory=list)
    scanned_fields: int = 0
    blocked: bool = False

    def summary(self) -> str:
        if not self.has_pii:
            return f"✅ PII 미검출 ({self.scanned_fields}개 필드 검사)"
        levels = [f["level"] for f in self.findings]
        return (
            f"⚠ PII {len(self.findings)}건 감지 "
            f"(CRITICAL: {levels.count('CRITICAL')}, "
            f"HIGH: {levels.count('HIGH')}) "
            f"— {'차단됨' if self.blocked else '경고'}"
        )


class PIIScanner:
    """PII 감지 및 차단 스캐너"""

    def __init__(self, fail_closed: bool = True, whitelist: list[str] = None):
        """
        Args:
            fail_closed: True면 PII 감지 시 차단 (기본값)
            whitelist: 추가 화이트리스트 패턴
        """
        self.fail_closed = fail_closed
        self._extra_whitelist = [re.compile(w) for w in (whitelist or [])]

    def _is_whitelisted(self, text: str, match: str) -> bool:
        """화이트리스트 패턴에 해당하는지 확인"""
        for wp in WHITELIST_PATTERNS + self._extra_whitelist:
            if wp.search(match):
                return True
        return False

    def scan_text(self, text: str) -> list[dict]:
        """단일 문자열에서 PII 검색"""
        if not text or not isinstance(text, str):
            return []

        findings = []
        for name, config in PII_PATTERNS.items():
            for match in config["pattern"].finditer(text):
                matched_text = match.group()
                if not self._is_whitelisted(text, matched_text):
                    findings.append({
                        "type": name,
                        "level": config["level"],
                        "description": config["description"],
                        "value_preview": matched_text[:4] + "****",
                        "position": match.start(),
                    })
        return findings

    def scan(self, data: Any, path: str = "") -> PIIScanResult:
        """딕셔너리/리스트/문자열에서 재귀적으로 PII 검색"""
        result = PIIScanResult()

        if isinstance(data, str):
            result.scanned_fields = 1
            findings = self.scan_text(data)
            if findings:
                for f in findings:
                    f["field_path"] = path
                result.findings.extend(findings)
                result.has_pii = True

        elif isinstance(data, dict):
            for key, value in data.items():
                # enc_ prefix 필드는 이미 암호화된 것이므로 스캔 건너뜀
                if key.startswith("enc_"):
                    continue
                sub = self.scan(value, path=f"{path}.{key}" if path else key)
                result.scanned_fields += sub.scanned_fields
                result.findings.extend(sub.findings)
                if sub.has_pii:
                    result.has_pii = True

        elif isinstance(data, (list, tuple)):
            for i, item in enumerate(data):
                sub = self.scan(item, path=f"{path}[{i}]")
                result.scanned_fields += sub.scanned_fields
                result.findings.extend(sub.findings)
                if sub.has_pii:
                    result.has_pii = True

        if self.fail_closed and result.has_pii:
            result.blocked = True

        return result

    def mask_text(self, text: str) -> str:
        """문자열에서 PII를 자동 마스킹"""
        if not text or not isinstance(text, str):
            return text

        masked = text
        for name, config in PII_PATTERNS.items():
            for match in config["pattern"].finditer(masked):
                matched_text = match.group()
                if not self._is_whitelisted(text, matched_text):
                    if name == "email":
                        local, domain = matched_text.split("@", 1)
                        replacement = f"{local[0]}****@{domain}"
                    elif "phone" in name:
                        replacement = matched_text[:3] + "-****-" + matched_text[-4:]
                    elif "name" in name:
                        replacement = matched_text[:2] + "****"
                    else:
                        replacement = matched_text[:3] + "****"
                    masked = masked.replace(matched_text, replacement, 1)
        return masked

    def mask_dict(self, data: dict, exclude_keys: set = None) -> dict:
        """딕셔너리의 모든 문자열 필드를 마스킹"""
        exclude = exclude_keys or set()
        result = {}
        for key, value in data.items():
            if key in exclude or key.startswith("enc_"):
                result[key] = value
            elif isinstance(value, str):
                result[key] = self.mask_text(value)
            elif isinstance(value, dict):
                result[key] = self.mask_dict(value, exclude)
            elif isinstance(value, list):
                result[key] = [
                    self.mask_dict(item, exclude) if isinstance(item, dict)
                    else self.mask_text(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def scan_and_block(self, data: dict) -> tuple[bool, dict, PIIScanResult]:
        """스캔 후 PII 있으면 마스킹된 버전 반환

        Returns:
            (is_safe, data, scan_result)
            - is_safe=True: 원본 데이터 안전
            - is_safe=False: 마스킹된 데이터 반환 (원본 차단)
        """
        result = self.scan(data)
        if result.has_pii and self.fail_closed:
            masked = self.mask_dict(data)
            return False, masked, result
        return True, data, result


# ─── 테스트 ──────────────────────────────────────────────
if __name__ == "__main__":
    scanner = PIIScanner(fail_closed=True)

    print("=" * 60)
    print("BRIDGE PII 스캐너 테스트")
    print("=" * 60)

    # 1. 안전한 데이터
    safe_data = {
        "region": "서울",
        "city": "구로",
        "teaching_age": "Kindy - Elem",
        "salary_krw": 2400000,
    }
    r1 = scanner.scan(safe_data)
    print(f"\n1. 안전한 데이터: {r1.summary()}")

    # 2. PII 포함 데이터
    unsafe_data = {
        "region": "서울",
        "contact_info": "김테스원장 010-2542-6545 test@gmail.com",
        "memo": "(서울 구로 해피해피 김테스원장 010-2542-6545)",
    }
    r2 = scanner.scan(unsafe_data)
    print(f"\n2. PII 포함 데이터: {r2.summary()}")
    for f in r2.findings:
        print(f"   → [{f['level']}] {f['description']}: {f['value_preview']} (필드: {f['field_path']})")

    # 3. Fail-Closed 테스트
    is_safe, output, r3 = scanner.scan_and_block(unsafe_data)
    print(f"\n3. Fail-Closed: safe={is_safe}, blocked={r3.blocked}")
    print(f"   마스킹된 contact_info: {output.get('contact_info')}")
    print(f"   마스킹된 memo: {output.get('memo')}")

    # 4. 화이트리스트 테스트
    whitelist_data = {
        "job_id": "Job. 1003",
        "website": "bridgejob.co.kr",
        "sender": "bridgejobkr@gmail.com",
    }
    r4 = scanner.scan(whitelist_data)
    print(f"\n4. 화이트리스트 데이터: {r4.summary()}")
