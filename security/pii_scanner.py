"""
security/pii_scanner.py — BRIDGE Outbound PII Scanner
=======================================================
PIIScanner: outbound 데이터에서 PII 자동 감지/차단/마스킹

감지 대상:
- 한국 전화번호 (010/02/031 등)
- 이메일 주소
- 직함+이름 (원장, 대표, 사장 등)
- 카카오ID
- 여권번호
- 외국인등록번호

화이트리스트:
- bridgejob.co.kr 도메인
- bridgejobkr@gmail.com, bridgejobkr@naver.com
- Job 번호 (JOB-xxx 등)
- 날짜 형식 (2026-03-06 등)
"""

import re
import json
from dataclasses import dataclass, field
from typing import Optional


# ── 화이트리스트 ──────────────────────────────────────────────────────────────
WHITELIST_EMAILS = {
    "bridgejobkr@gmail.com",
    "bridgejobkr@naver.com",
    "info@bridgejob.co.kr",
    "support@bridgejob.co.kr",
}
WHITELIST_DOMAINS = {"bridgejob.co.kr"}
WHITELIST_PATTERNS = [
    re.compile(r"JOB[-_]?\d+", re.IGNORECASE),                  # Job번호
    re.compile(r"\d{4}[-/]\d{2}[-/]\d{2}"),                      # 날짜
    re.compile(r"\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}"),       # 날짜+시간
    re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),          # IP 주소 (로그용)
]

# ── PII 탐지 패턴 ────────────────────────────────────────────────────────────
PII_DETECTORS = {
    "phone_kr": re.compile(
        r"(?<!\d)(0\d{1,2})[-\s.]?(\d{3,4})[-\s.]?(\d{4})(?!\d)"
    ),
    "email": re.compile(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    ),
    "name_with_title": re.compile(
        r"[\uAC00-\uD7A3]{2,5}\s*(원장|대표|사장|이사|부장|과장|차장|팀장|실장|소장|관장|선생|님)"
    ),
    "kakao_id": re.compile(
        r"(?:kakao|카카오)\s*(?:id|아이디|ID)\s*[:=\s]\s*(\S+)", re.IGNORECASE
    ),
    "passport": re.compile(
        r"[A-Z]{1,2}\d{7,8}"
    ),
    "alien_registration": re.compile(
        r"\d{6}[-\s]?\d{7}"
    ),
}


@dataclass
class PIIFinding:
    """PII 감지 결과 단건."""
    field_name: str
    pii_type: str
    value: str          # 감지된 원본 값 (마스킹 전)
    masked: str         # 마스킹된 값


@dataclass
class PIIScanResult:
    """PII 스캔 결과."""
    has_pii: bool = False
    findings: list = field(default_factory=list)
    blocked: bool = False


class PIIScanner:
    """Outbound PII 감지 + fail-closed 차단."""

    def __init__(self, fail_closed: bool = True):
        self.fail_closed = fail_closed

    def _is_whitelisted(self, value: str) -> bool:
        """화이트리스트 여부 확인."""
        if not value:
            return True
        lower = value.lower().strip()
        # 이메일 화이트리스트
        if lower in WHITELIST_EMAILS:
            return True
        # 도메인 화이트리스트
        for domain in WHITELIST_DOMAINS:
            if lower.endswith(f"@{domain}"):
                return True
        # 패턴 화이트리스트 (Job번호, 날짜 등)
        for pattern in WHITELIST_PATTERNS:
            if pattern.fullmatch(value):
                return True
        return False

    def _mask_value(self, value: str, pii_type: str) -> str:
        """PII 유형별 마스킹."""
        if pii_type == "phone_kr":
            clean = re.sub(r"[\s\-.]", "", value)
            if len(clean) >= 8:
                return clean[:3] + "-****-" + clean[-4:]
            return "****"
        elif pii_type == "email":
            if "@" not in value:
                return "****"
            local, domain = value.rsplit("@", 1)
            return f"{local[0]}****@{domain}" if len(local) > 1 else f"****@{domain}"
        elif pii_type == "name_with_title":
            parts = value.strip()
            if len(parts) >= 2:
                return parts[0] + "**" + (parts[-1] if re.match(r"[원대사이부과차팀실소관선]", parts[-1]) else "")
            return "**"
        elif pii_type in ("passport", "alien_registration"):
            if len(value) > 4:
                return value[:2] + "*" * (len(value) - 4) + value[-2:]
            return "****"
        elif pii_type == "kakao_id":
            return "****"
        return "****"

    def scan(self, data) -> PIIScanResult:
        """
        데이터에서 PII 감지.
        data: str, dict, or list
        """
        result = PIIScanResult()
        self._scan_recursive(data, "", result)
        if result.findings:
            result.has_pii = True
            if self.fail_closed:
                result.blocked = True
        return result

    def _scan_recursive(self, data, path: str, result: PIIScanResult):
        """재귀적 PII 스캔."""
        if isinstance(data, str):
            self._scan_text(data, path, result)
        elif isinstance(data, dict):
            for key, value in data.items():
                self._scan_recursive(value, f"{path}.{key}" if path else key, result)
        elif isinstance(data, (list, tuple)):
            for idx, item in enumerate(data):
                self._scan_recursive(item, f"{path}[{idx}]", result)

    def _scan_text(self, text: str, field_name: str, result: PIIScanResult):
        """텍스트에서 PII 패턴 매칭."""
        if not text or len(text) < 4:
            return

        for pii_type, pattern in PII_DETECTORS.items():
            for match in pattern.finditer(text):
                matched_value = match.group(0)
                if self._is_whitelisted(matched_value):
                    continue
                finding = PIIFinding(
                    field_name=field_name or "(root)",
                    pii_type=pii_type,
                    value=matched_value,
                    masked=self._mask_value(matched_value, pii_type),
                )
                result.findings.append(finding)

    def scan_and_block(self, data) -> tuple:
        """
        PII 스캔 + 차단.
        Returns: (is_safe, safe_data, scan_result)
        - is_safe=True: PII 없음, 원본 데이터 반환
        - is_safe=False: PII 감지, 마스킹된 데이터 반환
        """
        scan_result = self.scan(data)
        if not scan_result.has_pii:
            return (True, data, scan_result)

        # PII 감지 -> 자동 마스킹
        safe_data = self._mask_data(data)
        return (False, safe_data, scan_result)

    def _mask_data(self, data):
        """데이터 전체 PII 마스킹."""
        if isinstance(data, str):
            return self.mask_text(data)
        elif isinstance(data, dict):
            return {k: self._mask_data(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple)):
            return [self._mask_data(item) for item in data]
        return data

    def mask_text(self, text: str) -> str:
        """텍스트에서 PII 자동 마스킹."""
        if not text or not isinstance(text, str):
            return text

        result = text
        for pii_type, pattern in PII_DETECTORS.items():
            def _replacer(match, _type=pii_type):
                matched = match.group(0)
                if self._is_whitelisted(matched):
                    return matched
                return self._mask_value(matched, _type)
            result = pattern.sub(_replacer, result)
        return result

    def mask_dict(self, data: dict) -> dict:
        """dict 전체 필드 마스킹."""
        if not isinstance(data, dict):
            return data
        return {k: self._mask_data(v) for k, v in data.items()}


# ── Self-test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[pii_scanner] Self-test start...")
    scanner = PIIScanner(fail_closed=True)
    all_passed = True

    # 1. 전화번호 감지
    r1 = scanner.scan("연락처: 010-1234-5678")
    ok1 = r1.has_pii and any(f.pii_type == "phone_kr" for f in r1.findings)
    print(f"  [{'PASS' if ok1 else 'FAIL'}] phone detection: {r1.has_pii}")
    if not ok1:
        all_passed = False

    # 2. 이메일 감지
    r2 = scanner.scan({"contact": "user@example.com"})
    ok2 = r2.has_pii and any(f.pii_type == "email" for f in r2.findings)
    print(f"  [{'PASS' if ok2 else 'FAIL'}] email detection: {r2.has_pii}")
    if not ok2:
        all_passed = False

    # 3. 화이트리스트 통과
    r3 = scanner.scan("문의: bridgejobkr@gmail.com")
    ok3 = not r3.has_pii
    print(f"  [{'PASS' if ok3 else 'FAIL'}] whitelist pass: {not r3.has_pii}")
    if not ok3:
        all_passed = False

    # 4. 직함+이름 감지
    r4 = scanner.scan("담당자: 김철수원장")
    ok4 = r4.has_pii and any(f.pii_type == "name_with_title" for f in r4.findings)
    print(f"  [{'PASS' if ok4 else 'FAIL'}] name+title detection: {r4.has_pii}")
    if not ok4:
        all_passed = False

    # 5. scan_and_block
    is_safe, safe_data, _ = scanner.scan_and_block({"phone": "010-5555-6666", "id": 1})
    ok5 = not is_safe and "****" in str(safe_data)
    print(f"  [{'PASS' if ok5 else 'FAIL'}] scan_and_block: safe={is_safe}, masked={safe_data}")
    if not ok5:
        all_passed = False

    # 6. mask_text
    masked = scanner.mask_text("전화 010-9876-5432, 메일 user@test.com")
    ok6 = "****" in masked and "010-9876-5432" not in masked
    print(f"  [{'PASS' if ok6 else 'FAIL'}] mask_text: {masked}")
    if not ok6:
        all_passed = False

    # 7. 날짜 화이트리스트
    r7 = scanner.scan("날짜: 2026-03-06")
    ok7 = not r7.has_pii
    print(f"  [{'PASS' if ok7 else 'FAIL'}] date whitelist: {not r7.has_pii}")
    if not ok7:
        all_passed = False

    if all_passed:
        print("\n  All PII scanner tests PASSED.")
    else:
        print("\n  Some tests FAILED.")
