"""
pii_engine.py — BRIDGE Resume Converter
PII 탐지 + 삭제 (2레이어 + 집중점검)

Layer 1: regex (전화/이메일/주소/SNS/학교명/근무처/PII라벨)
Layer 2: Claude API (이름/업체명/추천서 서명)

v2.7 동기화 (2026-04-02):
- 아파트/빌라/오피스텔 등 한국 거주지 삭제
- 학교명 패턴 (RE_SCHOOL_NAMED / RE_UNIV_OF)
- 미국 도시+주 / 외국 도시+국가 삭제
- 전화번호 연도 False Positive 차단
- KR_WORKPLACE_KEYWORDS 확장
- PII 라벨 줄 삭제 (nationality/race/religion/gender/dob 등)
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

# 한국 거주지 (아파트/빌라/오피스텔 등) — v2.7
RE_KR_RESIDENTIAL = re.compile(
    r"[가-힣A-Za-z0-9]+\s*"
    r"(?:\d+\s*(?:단지|차|블록|동|호)?[가-힣]?\s*)?"
    r"(?:아파트|빌라|오피스텔|주공|자이|푸르지오|래미안|힐스테이트|더샵|sk뷰|sk view|e편한세상|"
    r"이편한세상|롯데캐슬|브라운스톤|경남아너스빌|포스코더샵|두산위브|대림|현대|삼성|"
    r"lh|sh|한신|부영|우미|중흥|반도|효성|동원|태영|제일|신동아|진흥|극동|청솔|"
    r"트리지움|위브|어울림|센트럴|파크|팰리스|아이파크|더리버|하늘채|금호|한라|"
    r"apartment|apt|villa|officetel)",
    re.IGNORECASE,
)

# 학교명 패턴 — v2.7
RE_SCHOOL_NAMED = re.compile(
    r"\b[A-Z][A-Za-z'\-\s]{2,40}"
    r"(?:Primary|Secondary|High|Middle|Junior|Grammar|Prep|Preparatory|"
    r"Independent|International|National|Christian|Catholic|Islamic|"
    r"Montessori|Waldorf|Academy|College|Institute|Seminary)"
    r"(?:\s+School|\s+College|\s+Academy)?\b",
)
RE_UNIV_OF = re.compile(
    r"\b(?:University|Université|Universidad|Universität|Università)\s+of\s+[A-Z][A-Za-z\s\-]{2,40}\b",
)

# 미국 도시+주 — v2.7
RE_US_CITY_STATE = re.compile(
    r"\b(?:New York|Los Angeles|Chicago|Houston|Phoenix|Philadelphia|"
    r"San Antonio|San Diego|Dallas|San Jose|Austin|Jacksonville|"
    r"Fort Worth|Columbus|Charlotte|Indianapolis|San Francisco|Seattle|"
    r"Denver|Nashville|Oklahoma City|El Paso|Washington|Boston|"
    r"Las Vegas|Memphis|Louisville|Baltimore|Milwaukee|Albuquerque|"
    r"Tucson|Fresno|Sacramento|Mesa|Kansas City|Atlanta|Omaha|"
    r"Colorado Springs|Raleigh|Long Beach|Virginia Beach|Minneapolis|"
    r"Tampa|New Orleans|Arlington|Wichita|Bakersfield|Aurora|"
    r"Anaheim|Santa Ana|Corpus Christi|Riverside|St\. Louis|Lexington|"
    r"Stockton|Pittsburgh|Anchorage|Greensboro|Lincoln|Orlando|"
    r"Newark|Plano|Henderson|Durham|Fort Wayne|Jersey City|Laredo|"
    r"Chandler|Madison|Lubbock|Norfolk|Cleveland|Garland|Scottsdale|"
    r"Irving|Baton Rouge|Reno|Hialeah|Chesapeake|Gilbert|Portland)"
    r"(?:,\s*[A-Z]{2})?\b",
)

# 외국 도시+국가 — v2.7
RE_FOREIGN_CITY = re.compile(
    r"\b(?:London|Manchester|Birmingham|Liverpool|Sheffield|Leeds|Bristol|"
    r"Glasgow|Edinburgh|Cardiff|Belfast|Oxford|Cambridge|Sydney|Melbourne|"
    r"Brisbane|Perth|Adelaide|Auckland|Wellington|Christchurch|Toronto|"
    r"Vancouver|Montreal|Calgary|Ottawa|Singapore|Kuala Lumpur|Hong Kong|"
    r"Beijing|Shanghai|Guangzhou|Shenzhen|Tokyo|Osaka|Bangkok|Manila|"
    r"Jakarta|Dhaka|Mumbai|Delhi|Dubai|Johannesburg|Cape Town|Nairobi|"
    r"Lagos|Accra|Harare|Lusaka|Dar es Salaam|Kampala|Kigali)"
    r"(?:,?\s*(?:UK|England|Scotland|Wales|Australia|New Zealand|Canada|"
    r"Singapore|Malaysia|China|Japan|Thailand|Philippines|Indonesia|"
    r"Bangladesh|India|UAE|South Africa|Kenya|Nigeria|Ghana|Zimbabwe|"
    r"Zambia|Tanzania|Uganda|Rwanda))?\b",
    re.IGNORECASE,
)

# 한국 학원/교육기관 키워드 (업체명 탐지용) — v2.7 확장 + v2.8 학원명 추가
_KR_WORKPLACE = re.compile(
    r"(?:[A-Za-z가-힣]{2,30}"
    r"(?:어학원|학원|학교|유치원|학습원|교육원|교습소|유아원|영어학원|"
    r"english\s*school|language\s*school|primary\s*school|secondary\s*school|"
    r"independent\s*school|grammar\s*school|boarding\s*school|prep\s*school|"
    r"kindergarten|nursery|tutoring|hagwon|institute|academy|center|centre)"
    r"|Wonderland|King'?s\s*Speech|English\s*Village|Global\s*Village|Brown\s*Bears"
    r"|Smart\s*Tree|English\s*Eye|MBC\s*English|GEM\s*Academy"
    r"|Saint\s*Paul\s*American\s*Scholars|GCIS|Kids\s*Club|Worwick|BIE|IEB|GEA|SIE|DIS"
    r"|KIS\s*Academy|CDI|Willson\s*English|GGE\s*English|3030\s*English"
    r"|Kids\s*Town|English\s*City)",
    re.IGNORECASE,
)

# ── 수정 1: 대학/칼리지 이름 보존 키워드 ─────────────────────────────────────
PRESERVE_INSTITUTION = [
    "University", "College", "Institute of Technology",
    "Graduate School", "Seminary", "Polytechnic",
]

# ── 수정 3: 직함/스킬 내 보호 패턴 ──────────────────────────────────────────
_TITLE_SAFE_RE = re.compile(
    r"(?:Middle\s+School|High\s+School|Elementary\s+School|Language\s+School|"
    r"English\s+Language|English\s+Teacher|English\s+Education|English\s+Development|"
    r"School\s+Teacher|Pre-?School|Preschool)",
    re.IGNORECASE,
)

# ── 수정 2: 교육 섹션 헤더 감지 ──────────────────────────────────────────────
_EDU_HDR_RE = re.compile(
    r"^\s*(?:EDUCATION|ACADEMIC\s+BACKGROUND|QUALIFICATIONS?|CERTIFICATIONS?|DEGREES?)\s*:?\s*$",
    re.IGNORECASE,
)
_NON_EDU_HDR_RE = re.compile(
    r"^\s*(?:EXPERIENCE|WORK\s*HISTORY|EMPLOYMENT|SKILLS?|REFERENCES?|LANGUAGES?|"
    r"PERSONAL|PROFILE|SUMMARY|CAREER|PROFESSIONAL)\s*:?\s*$",
    re.IGNORECASE,
)

# ── 수정 4: 한국 도시명 (영문) ────────────────────────────────────────────────
_KR_CITIES_LIST = [
    "Seoul", "Busan", "Daegu", "Incheon", "Gwangju", "Daejeon",
    "Ulsan", "Sejong", "Suwon", "Seongnam", "Yongin", "Goyang",
    "Changwon", "Cheongju", "Jeonju", "Cheonan", "Ansan", "Anyang",
    "Gimhae", "Pohang", "Uijeongbu", "Paju", "Gimpo", "Jeju",
    "Chuncheon", "Mokpo", "Gunsan", "Wonju", "Iksan", "Gyeongju",
    "Yangsan", "Asan", "Gumi", "Tongyeong", "Sacheon", "Geoje",
    "Hanam", "Osan", "Icheon", "Gwangmyeong", "Siheung",
    "Pyeongtaek", "Gwacheon", "Dongducheon", "Pocheon",
    "Gangneung", "Sokcho", "Samcheok", "Taebaek", "Yeongju",
    "Andong", "Gimcheon", "Mungyeong", "Sangju", "Yeongcheon",
    "Gyeongsan", "Chilgok", "Dalseong", "Yongsan", "Gangnam",
    "Songpa", "Mapo", "Seodaemun", "Dongjak", "Gwanak",
    "Nowon", "Dobong", "Gangbuk", "Seongbuk", "Jungnang",
    "Gwangjin", "Dongdaemun", "Jongno", "Yeongdeungpo",
    "Guro", "Geumcheon", "Gangseo", "Yangcheon", "Eunpyeong",
    "Songdo", "Bundang", "Ilsan", "Pangyo", "Suji",
    "Haeundae", "Sasang", "Saha", "Yeonje", "Suyeong",
    "Geumjeong", "Dongnae", "Busanjin", "Yeongdo",
]
_KR_CITY_RE = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in sorted(_KR_CITIES_LIST, key=len, reverse=True)) + r")"
    r"(?:,?\s*(?:South\s+Korea|Korea))?\b",
    re.IGNORECASE,
)

# ── 수정 5/6: 한국 학원 고유명사 목록 (긴 이름 우선) ─────────────────────────
_KR_ACADEMY_LIST = sorted(list(set([
    "April English", "Wall Street English", "Ivy League English",
    "King's Academy", "GEM Academy", "Stanford Academy", "Berkeley Academy",
    "Pinetree Academy", "Cedar Academy", "Oxford Academy", "Cambridge Institute",
    "KIS Academy", "Princeton Review",
    "Mount Pisgah", "Morning Calm", "Pine Division", "Blue Mountain",
    "Maple Bear", "Little Fox", "Reading Town", "English Village",
    "Global Village", "Brown Bears", "Smart Tree", "English Eye",
    "MBC English", "Broad Language", "Chuncheon Elementary",
    "English Born", "English Vine", "English City", "English Egg",
    "Toss English", "3030 English", "GGE English", "Willson English",
    "MuM English", "York English", "James Cook",
    "Talking Club", "Reading Gate", "Wonder Island", "Apple Tree",
    "King's Speech", "Brown Bags", "Kids College",
    "Kids Town", "Kids Club", "Ivy Kids",
    "Helen Doron", "GrapeSEED", "Creverse", "Langcon",
    "Brighton Junior", "Union English", "Elite Prep", "Fast One",
    "Wiz Island", "Haba League", "Prime Unyang", "Francis Parker",
    "Herald School", "E-Public", "Berlitz",
    "Chungdahm", "Altiora", "Pagoda", "Avalon",
    "To-Be", "i-Garten", "Twinklers", "K-First",
    "S-KIDS", "Toppia", "Plato", "Lexis",
    "Saint Paul", "Hillside", "Worwick",
    "Yoon's English",
    "Poly", "Rise", "YBM", "ECC", "CDI", "GnB", "DYB", "SLP",
    "JLS", "PSA", "LCI", "OHC", "BIE", "IEB", "GEA", "SIE", "DIS",
    "GCIS", "Sei", "Kaplan",
])), key=len, reverse=True)
_KR_ACADEMY_RE = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in _KR_ACADEMY_LIST) + r")"
    r"(?:\s+(?:English|Language|Academy|School|Institute|Center|Centre|학원))?\b",
    re.IGNORECASE,
)

# Reference 섹션 헤더 패턴 — v2.8
_REF_HEADER_RE = re.compile(
    r"(?im)^[ \t]*(?:references?|referees?|references?\s+available(?:\s+on\s+request)?)\s*$"
)

def remove_reference_section(text: str) -> str:
    """References/Referees 섹션 헤더부터 끝까지 삭제."""
    m = _REF_HEADER_RE.search(text)
    if not m:
        return text
    return text[:m.start()].rstrip()


# PII 라벨 줄 삭제 — v2.7
_PII_LABEL_RE = re.compile(
    r"^[^\n]*\b(?:nationality|citizenship|race|ethnicity|religion|"
    r"date\s+of\s+birth|birth\s+date|dob|gender|sex)\b[^\n]*$",
    re.IGNORECASE | re.MULTILINE,
)

def _is_year_range(matched: str) -> bool:
    """전화번호처럼 보이는 연도 범위(2017-2021 등) 여부 판별."""
    digits = re.findall(r"\d+", matched)
    return bool(digits) and all(1900 <= int(d) <= 2099 for d in digits)


def _apply_regex(text: str) -> tuple[str, list[PIIMatch]]:
    """regex 패턴으로 PII 감지 + 마스킹."""
    found:   list[PIIMatch] = []
    cleaned: str = text

    # ── 기본 패턴 (전화/이메일/주소/SNS) ──────────────────────────────────
    for ptype, pattern in _PATTERNS.items():
        for m in pattern.finditer(cleaned):
            # 전화번호 False Positive: 연도 범위(2017-2021 등) 차단
            if ptype in ("phone_kr", "phone_intl") and _is_year_range(m.group(0)):
                continue
            replacement = f"[{ptype.upper()}_REMOVED]"
            found.append(PIIMatch(
                type=ptype,
                original_value=m.group(0),
                position=m.start(),
                confidence=0.95,
                color="red",
            ))
            cleaned = cleaned.replace(m.group(0), replacement, 1)

    # ── 한국 거주지 (아파트명 등) ─────────────────────────────────────────
    for m in RE_KR_RESIDENTIAL.finditer(cleaned):
        found.append(PIIMatch(
            type="address",
            original_value=m.group(0),
            position=m.start(),
            confidence=0.90,
            color="red",
        ))
        cleaned = cleaned.replace(m.group(0), "South Korea", 1)

    # ── 학교명 (줄 단위 스캔) — 수정 1/2/3/7 적용 ───────────────────────────
    lines = cleaned.split("\n")
    new_lines = []
    in_edu_section = False
    for i, line in enumerate(lines):
        # 수정 2: 섹션 헤더 추적
        if _EDU_HDR_RE.match(line):
            in_edu_section = True
        elif _NON_EDU_HDR_RE.match(line):
            in_edu_section = False

        # 수정 7: 인접 줄(±2) 한국 컨텍스트 확인
        window = " ".join(lines[max(0, i - 2):i + 3])
        has_kr_ctx = bool(
            re.search(r"\b(?:South\s+Korea|Korea|한국)\b", window, re.IGNORECASE)
            or _KR_CITY_RE.search(window)
            or re.search(r"[가-힣]", window)
        )

        # RE_SCHOOL_NAMED 처리 (수정 1/2/3/7)
        for m in RE_SCHOOL_NAMED.finditer(line):
            orig = m.group(0)
            # 수정 1: 대학/칼리지 이름 보존
            if any(kw.lower() in orig.lower() for kw in PRESERVE_INSTITUTION):
                continue
            # 수정 3: 직함/스킬 내 보호 패턴
            if _TITLE_SAFE_RE.search(orig):
                continue
            # 수정 2: 교육 섹션 내 학위/전공명 삭제 금지
            if in_edu_section:
                continue
            # 수정 7: 해외 기관 보존 (한국 컨텍스트 없으면 스킵)
            if not has_kr_ctx:
                continue
            repl = "School" if "school" in orig.lower() else "University"
            found.append(PIIMatch(
                type="company",
                original_value=orig,
                position=0,
                confidence=0.85,
                color="red",
            ))
            line = line.replace(orig, repl, 1)

        # RE_UNIV_OF: 수정 1 — University of X 형태는 항상 보존
        # (삭제하지 않음)

        new_lines.append(line)
    cleaned = "\n".join(new_lines)

    # ── 미국 도시+주 ──────────────────────────────────────────────────────
    for m in RE_US_CITY_STATE.finditer(cleaned):
        found.append(PIIMatch(
            type="address",
            original_value=m.group(0),
            position=m.start(),
            confidence=0.88,
            color="red",
        ))
        cleaned = cleaned.replace(m.group(0), "South Korea", 1)

    # ── 외국 도시+국가 ────────────────────────────────────────────────────
    for m in RE_FOREIGN_CITY.finditer(cleaned):
        found.append(PIIMatch(
            type="address",
            original_value=m.group(0),
            position=m.start(),
            confidence=0.85,
            color="red",
        ))
        cleaned = cleaned.replace(m.group(0), "South Korea", 1)

    # ── 수정 4: 한국 도시명 → "South Korea" ──────────────────────────────────
    for m in _KR_CITY_RE.finditer(cleaned):
        orig = m.group(0)
        found.append(PIIMatch(
            type="address",
            original_value=orig,
            position=m.start(),
            confidence=0.88,
            color="red",
        ))
        cleaned = cleaned.replace(orig, "South Korea", 1)

    # ── 수정 5/6/7: 한국 학원/교육기관 (컨텍스트 확인 + 전체 토큰 교체) ──────
    lines3 = cleaned.split("\n")
    new_lines3 = []
    for i, line in enumerate(lines3):
        window3 = " ".join(lines3[max(0, i - 2):i + 3])
        has_kr3 = bool(
            re.search(r"\b(?:South\s+Korea|Korea|한국)\b", window3, re.IGNORECASE)
            or _KR_CITY_RE.search(window3)
            or re.search(r"[가-힣]", window3)
        )
        has_foreign3 = bool(
            RE_FOREIGN_CITY.search(window3) or RE_US_CITY_STATE.search(window3)
        )

        # KR_ACADEMY_RE: 고유명사 (수정 5/6/7)
        for m in _KR_ACADEMY_RE.finditer(line):
            orig = m.group(0)
            # 수정 7: 해외 컨텍스트가 명확하고 한국 컨텍스트 없으면 보존
            if has_foreign3 and not has_kr3:
                continue
            # 수정 3: 직함/스킬 내 TITLE_SAFE 보호 (한국 컨텍스트도 없을 때만)
            if _TITLE_SAFE_RE.search(line) and not has_kr3:
                continue
            found.append(PIIMatch(
                type="company",
                original_value=orig,
                position=0,
                confidence=0.90,
                color="red",
            ))
            line = line.replace(orig, "English Academy", 1)

        # 일반 KR_WORKPLACE: 한국 컨텍스트 필수 (수정 6/7)
        if has_kr3:
            for m in _KR_WORKPLACE.finditer(line):
                orig = m.group(0)
                # 수정 6: TITLE_SAFE 패턴이면 스킵
                if _TITLE_SAFE_RE.search(orig):
                    continue
                found.append(PIIMatch(
                    type="company",
                    original_value=orig,
                    position=0,
                    confidence=0.90,
                    color="red",
                ))
                line = line.replace(orig, "English Academy", 1)

        new_lines3.append(line)
    cleaned = "\n".join(new_lines3)

    # ── PII 라벨 줄 삭제 (nationality/race/religion/gender/dob 등) ─────────
    cleaned = _PII_LABEL_RE.sub("", cleaned)

    # ── Reference 섹션 전체 삭제 ──────────────────────────────────────────
    cleaned = remove_reference_section(cleaned)

    return cleaned, found


# ── Layer 2: Claude API ────────────────────────────────────────────────────
_CLAUDE_MODEL = "claude-sonnet-4-6"

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
