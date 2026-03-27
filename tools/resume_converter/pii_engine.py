"""
pii_engine.py — BRIDGE Resume Converter
PII 탐지 + 삭제 (2레이어 + 집중점검)

Layer 1: regex (전화/이메일/주소/SNS)
Layer 2: Claude API (이름/업체명/추천서 서명)
"""

from __future__ import annotations

import os
import re
import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

# ── 로거 ──────────────────────────────────────────────────────────────────
log = logging.getLogger("pii_engine")

# ── 결과 타입 ─────────────────────────────────────────────────────────────
@dataclass
class PIIMatch:
    type:           str     # 'phone' | 'email' | 'address' | 'sns' | 'name' | 'company' | 'signature'
    original_value: str
    position:       int     # 문자열 오프셋
    confidence:     float   # 0.0 ~ 1.0
    color:          str = "red"  # 'red'(삭제확정) | 'yellow'(불확실) | 'green'(유지)

@dataclass
class PIIResult:
    cleaned_text: str
    pii_found:    List[PIIMatch] = field(default_factory=list)
    uncertain:    List[dict]     = field(default_factory=list)  # [{text, reason}]


# ── Layer 1: Regex 패턴 ────────────────────────────────────────────────────
_PATTERNS = {
    "phone_kr":  re.compile(r"(?:010|011|016|017|018|019)[-.\s]?\d{3,4}[-.\s]?\d{4}"),
    "phone_intl":re.compile(r"\+?\d{1,3}[-.\s]\(?\d{1,4}\)?[-.\s]\d{3,4}[-.\s]\d{3,4}"),
    "email":     re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    "addr_kr":   re.compile(
        r"(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)"
        r"[가-힣\s\d,.-]{2,40}"
        r"(?:시|구|동|로|길|번길|번지|읍|면|리)(?:\s*\d+)?",
    ),
    "kakao":     re.compile(r"(?:카카오|kakao|카톡)[:\s]?\s*(\S{3,30})", re.IGNORECASE),
    "sns":       re.compile(
        r"(?:instagram\.com|fb\.com|facebook\.com|twitter\.com|t\.me|line\.me|wechat|위챗)"
        r"[/\s]?\S{2,30}",
        re.IGNORECASE,
    ),
    "linkedin":  re.compile(
        r"(?:linkedin\.com/in/|linkedin:\s*)\S{3,60}",
        re.IGNORECASE,
    ),
}

# 한국 학원/교육기관 키워드 (업체명 탐지용 보조)
_KR_WORKPLACE = re.compile(
    r"[A-Za-z가-힣]{2,20}(?:어학원|학원|학교|유치원|학습원|교육원|교습소|유아원|영어학원)",
)

def _apply_regex(text: str) -> tuple[str, list[PIIMatch]]:
    """regex 패턴으로 PII 감지 + 마스킹."""
    found:   list[PIIMatch] = []
    cleaned: str = text
    offset = 0  # 마스킹 후 오프셋 보정

    for ptype, pattern in _PATTERNS.items():
        for m in pattern.finditer(text):
            replacement = f"[{ptype.upper()}_REMOVED]"
            found.append(PIIMatch(
                type=ptype,
                original_value=m.group(0),
                position=m.start() + offset,
                confidence=0.95,
                color="red",
            ))
            cleaned = cleaned.replace(m.group(0), replacement, 1)
            offset += len(replacement) - len(m.group(0))

    # 한국 학원명
    for m in _KR_WORKPLACE.finditer(text):
        replacement = "학원"
        found.append(PIIMatch(
            type="company",
            original_value=m.group(0),
            position=m.start(),
            confidence=0.90,
            color="red",
        ))
        cleaned = cleaned.replace(m.group(0), replacement, 1)

    return cleaned, found


# ── Layer 2: Claude API ────────────────────────────────────────────────────
_CLAUDE_MODEL = "claude-sonnet-4-20250514"

_SYSTEM_PROMPT = """You are a PII detector for Korean ESL teacher resumes.
Analyze the text and find:
1. Personal names (English and Korean)
2. Korean company/school names (학원, 학교, 어학원 names)
3. Signatures with name + affiliation + contact in recommendation letters
4. Any other identifying information

Return ONLY valid JSON with this exact structure:
{
  "to_remove": [
    {"text": "exact text to remove", "type": "name|company|signature|other", "replacement": "replacement text or empty string"}
  ],
  "uncertain": [
    {"text": "suspicious text", "reason": "why uncertain"}
  ]
}

Rules:
- Replace personal names with empty string ""
- Replace Korean school/company names with "학원" or "학교"
- Remove signatures entirely (name + affiliation + phone/email block)
- For uncertain items, do NOT remove, just flag them
- Return only JSON, no explanation"""

def _call_claude(text: str, api_key: str, focus: bool = False) -> dict:
    """Claude API 호출. focus=True 이면 집중점검 모드."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    user_msg = f"{'[FOCUS CHECK] ' if focus else ''}Detect PII in this text:\n\n{text[:8000]}"

    try:
        resp = client.messages.create(
            model=_CLAUDE_MODEL,
            max_tokens=2000,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = resp.content[0].text.strip()
        # JSON 추출
        m = re.search(r"\{[\s\S]+\}", raw)
        if m:
            return json.loads(m.group(0))
    except Exception as e:
        log.warning(f"Claude API 오류 (regex only 폴백): {e}")

    return {"to_remove": [], "uncertain": []}

def _apply_claude(text: str, claude_result: dict) -> tuple[str, list[PIIMatch], list[dict]]:
    """Claude 결과를 텍스트에 적용."""
    found:     list[PIIMatch] = []
    uncertain: list[dict]    = []
    cleaned    = text

    for item in claude_result.get("to_remove", []):
        orig        = item.get("text", "")
        replacement = item.get("replacement", "")
        ptype       = item.get("type", "unknown")
        if orig and orig in cleaned:
            found.append(PIIMatch(
                type=ptype,
                original_value=orig,
                position=cleaned.find(orig),
                confidence=0.88,
                color="red",
            ))
            cleaned = cleaned.replace(orig, replacement)

    for item in claude_result.get("uncertain", []):
        uncertain.append({
            "text":   item.get("text", ""),
            "reason": item.get("reason", ""),
        })

    return cleaned, found, uncertain


# ── 메인 함수 ──────────────────────────────────────────────────────────────
def analyze_pii(
    text:    str,
    api_key: str | None = None,
    focus:   bool = False,
) -> PIIResult:
    """
    전체 PII 분석 실행.

    Args:
        text:    분석할 텍스트
        api_key: Anthropic API 키 (없으면 regex only)
        focus:   True이면 Claude 집중점검 모드

    Returns:
        PIIResult
    """
    if not text or not text.strip():
        return PIIResult(cleaned_text=text)

    # Layer 1: regex
    cleaned1, found1 = _apply_regex(text)

    # Layer 2: Claude
    found2:     list[PIIMatch] = []
    uncertain:  list[dict]    = []

    if api_key:
        try:
            claude_result = _call_claude(cleaned1, api_key, focus)
            cleaned2, found2, uncertain = _apply_claude(cleaned1, claude_result)
        except Exception as e:
            log.warning(f"Claude 레이어 실패 (regex 결과 사용): {e}")
            cleaned2 = cleaned1
    else:
        log.info("API 키 없음 → regex only 모드")
        cleaned2 = cleaned1

    return PIIResult(
        cleaned_text=cleaned2,
        pii_found=found1 + found2,
        uncertain=uncertain,
    )


def analyze_pii_focus(text: str, api_key: str) -> PIIResult:
    """집중점검: 선택 텍스트만 Claude 재분석."""
    return analyze_pii(text, api_key, focus=True)


# ── 로드 API 키 ────────────────────────────────────────────────────────────
def load_api_key() -> Optional[str]:
    """환경변수 → vault → None 순서로 Anthropic API 키 로드."""
    # 1. 환경변수
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if key:
        return key

    # 2. vault
    vault_path = Path("Q:/Claudework/.vault/anthropic.key")
    if vault_path.exists():
        return vault_path.read_text(encoding="utf-8").strip()

    # 3. 같은 폴더 .api_key
    local = Path(__file__).parent / ".api_key"
    if local.exists():
        return local.read_text(encoding="utf-8").strip()

    return None


# ── CLI ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sample = """
    John Smith 선생님의 이력서입니다.
    연락처: 010-1234-5678 / john.smith@gmail.com
    주소: 서울 강남구 역삼동 123-45
    카카오: johnteacher
    ABC어학원 3년 근무
    """
    api_key = load_api_key()
    result  = analyze_pii(sample, api_key)
    print("=== 정리된 텍스트 ===")
    print(result.cleaned_text)
    print(f"\n=== 탐지 항목 {len(result.pii_found)}개 ===")
    for item in result.pii_found:
        print(f"  [{item.color}] {item.type}: {item.original_value[:40]}")
    if result.uncertain:
        print(f"\n=== 불확실 항목 {len(result.uncertain)}개 ===")
        for item in result.uncertain:
            print(f"  [yellow] {item['text']}: {item['reason']}")
