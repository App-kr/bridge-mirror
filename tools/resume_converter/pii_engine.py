"""
pii_engine.py — BRIDGE Resume Converter
PII 탐지 + 삭제 (2레이어 + 집중점검)

Layer 1: regex (전화/이메일/주소/SNS/학교명/근무처/PII라벨)
Layer 2: Claude API (이름/업체명/추천서 서명)

v3.0 (2026-04-22):
- _KR_ACADEMY_SHORT 기준 변경: ≤4자 → <4자 (Knox 등 4자 브랜드 LONG 처리)
- LONG 큐레이션 브랜드: Korea 컨텍스트 없어도 항상 익명화 (큐레이션 = 확실한 한국 브랜드)
- _NON_EDU_HDR_RE: PROFESSIONAL EXPERIENCES(복수형) 추가
- 커버레터 서명: "Yours sincerely,\n풀네임" → "Yours sincerely,\n첫이름" (결별인사 보존)
- _preserve_closing_firstname + 마커 시스템 (Layer 2 생존 보장)
- phone_bare 패턴: 구분자 없는 국제번호 +27670216180 등 처리
- addr_kr_en → "South Korea" 직접 대체 (마커 경유 맥락 소실 방지)
- _BARE_PERSONAL_RE: 국가명 단독 줄 삭제 확장
v2.9 (2026-04-22):
- has_kr_ctx 글로벌 폴백 제거 → 인접 ±2줄 직접 증거만 (해외 직장 보존)
- in_edu_section3 추가 → 교육 섹션 학교명·기관명 절대 보존
- _INST_SUFFIX 패턴 → 라인별 edu섹션+한국컨텍스트 조건 처리
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
    "phone_kr":   re.compile(r"(?:010|011|016|017|018|019)[-.\s]?\d{3,4}[-.\s]?\d{4}"),
    "phone_intl": re.compile(r"\+?\d{1,3}[-.\s]\(?\d{1,4}\)?[-.\s]\d{3,4}[-.\s]\d{3,4}"),
    # 구분자 없는 국제 전화: +27670216180 / +821012345678 / +447XXXXXXXXX
    # \b 사용 불가 (+ 앞은 word boundary 아님) — 앞뒤가 digit이 아닌 경우만 매칭
    "phone_bare": re.compile(
        r"(?<!\d)\+\d{7,15}(?!\d)",
    ),
    # US 국내 형식: NXX-NXX-XXXX (예: 445-900-3414 / (215) 555-1234)
    "phone_us":   re.compile(
        r"\b(?:\(?\d{3}\)?[-.\s])?\d{3}[-.\s]\d{4}\b"
        r"(?!\s*(?:19|20)\d{2})",  # 연도 뒤 숫자 차단
    ),
    "email":      re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    "addr_kr":    re.compile(
        r"(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)"
        r"[가-힣\s\d,.-]{2,40}"
        r"(?:시|구|동|로|길|번길|번지|읍|면|리)(?:\s*\d+)?",
    ),
    # 영문 한국 주소: Gasan-dong, South Korea / Mapo-gu, Seoul / Gasan-dong Seoul South Korea
    "addr_kr_en": re.compile(
        r"\b[A-Z][A-Za-z]+(?:-(?:dong|gu|si|ro|gil|eup|myeon|ri))"
        r"(?:[,\s]+(?:Seoul|Busan|Incheon|Daegu|Daejeon|Gwangju|Ulsan|Suwon|Seongnam))??"
        r"(?:[,\s]+(?:South\s+)?Korea)?\b"
        r"|"
        r"\b[A-Z][A-Za-z\-]+,\s*(?:Seoul|South\s+Korea|Korea)\b",
        re.IGNORECASE,
    ),
    # US/캐나다 거주지 주소: 123 Eagle Mount Dr., Richboro PA 18954
    # 대소문자 구분 필수 (IGNORECASE 없음) — "17 with an ave" 오탐 방지
    # 집 번호: 2~5자리 / 도로명: 대문자 시작 1~4 단어 / 도로 접미사: 대/소문자 모두 허용
    "addr_us":    re.compile(
        # ⚠️ \s → [ \t] 필수 — \s는 \n을 포함해 다음 줄까지 삼키는 버그 발생
        r"\b\d{2,5}[ \t]+"
        r"(?:[A-Z][A-Za-z'\-]+[ \t]+){1,4}"
        r"(?:Street|St|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Road|Rd|Lane|Ln|"
        r"Way|Court|Ct|Place|Pl|Circle|Cir|Mount|Mt|Highway|Hwy)"
        r"\.?(?:[, \t]+[A-Za-z]{2,20}(?:[ \t]+[A-Z]{2})?)?(?:[, \t]*\d{5}(?:-\d{4})?)?",
    ),
    # kakao ID: "kakao ID kamogelo30" / "KakaoTalk: user123" / "카카오: xxx"
    "kakao":      re.compile(
        r"(?:카카오|kakao|카톡)(?:\s*(?:talk|id|아이디|ID))?[:\s]+\S{3,30}",
        re.IGNORECASE,
    ),
    "sns":        re.compile(
        r"(?:instagram\.com|fb\.com|facebook\.com|twitter\.com|t\.me|line\.me|wechat|위챗)"
        r"[/\s]?\S{2,30}",
        re.IGNORECASE,
    ),
    "linkedin":   re.compile(
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
    r"한신|부영|우미|중흥|반도|효성|동원|태영|제일|신동아|진흥|극동|청솔|"
    r"트리지움|위브|어울림|센트럴|파크|팰리스|아이파크|더리버|하늘채|금호|한라)"
    # 영문 아파트 키워드: 단어 경계 필수 (adapt, aptitude 오탐 방지)
    r"|\b(?:apartment|apt|officetel)\b",
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
    r"|Saint\s*Paul\s*American\s*Scholars|GCIS|Kids\s*Club|Worwick"
    r"|KIS\s*Academy|CDI|Willson\s*English|GGE\s*English|3030\s*English"
    r"|Kids\s*Town|English\s*City)",
    # BIE/IEB/GEA/SIE/DIS 제거: _KR_ACADEMY_RE_SHORT에서 대소문자 구분으로 처리
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
    r"^\s*(?:EXPERIENCE|WORK\s*(?:EXPERIENCE|HISTORY)|EMPLOYMENT(?:\s+HISTORY)?|"
    r"PROFESSIONAL\s+EXPERIENCES?|CAREER\s+HISTORY|JOB\s+HISTORY|"
    r"SKILLS?|REFERENCES?|LANGUAGES?|PERSONAL|PROFILE|SUMMARY|CAREER|PROFESSIONAL)\s*:?\s*$",
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
    # 추가 — 학원 소재지로 자주 등장하는 지역 (v2.9)
    "Dongtan", "Mokdong", "Sangnok", "Ilsan", "Masan", "Gimpo",
    "Nowon", "Gapyeong", "Namyangju", "Uiwang", "Gunpo",
    "Gwangyang", "Suncheon", "Yeosu", "Jinju", "Geoje",
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
    # v2.9 추가 — 실제 등장 한국 학원명
    "Oeadea", "Deadea", "Deokso",
    "Poly", "Rise", "YBM", "ECC", "CDI", "GnB", "DYB", "SLP",
    "JLS", "PSA", "LCI", "OHC", "BIE", "IEB", "GEA", "SIE", "DIS",
    "GCIS", "Sei", "Kaplan", "YEP",
    # v3.0 추가 — 자주 등장하는 한국 학원/교육기관 브랜드명
    # (SA/해외에도 같은 이름 존재할 수 있으므로 _doc_has_korea 컨텍스트 필요)
    "Knox", "Avalon", "Poly School", "Chungdahm Learning",
    "Wall Street", "Jungchul", "Kangaroo",
    "JungAng", "Modeun", "Winkers", "Stepping Stones",
    "Cocoa", "Maple", "Ivy", "Rainbow", "Sunshine", "Cosmos",
    "Wonderkids", "Little Stars", "Bright Stars",
    "Eduplex", "Edu Bridge",
])), key=len, reverse=True)
# 3자 이하 약어(YBM, DIS, SLP 등): 대소문자 구분 필수 → 소문자 오탐(dis, sei…) 방지
# 4자 이상은 LONG으로 처리 — Knox(4), Poly(4), Rise(4) 등은 한국 컨텍스트 없어도 익명화
_KR_ACADEMY_SHORT = [n for n in _KR_ACADEMY_LIST if len(n) < 4]
_KR_ACADEMY_LONG  = [n for n in _KR_ACADEMY_LIST if len(n) >= 4]

_KR_ACADEMY_RE_LONG = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in _KR_ACADEMY_LONG) + r")"
    r"(?:\s+(?:English|Language|Academy|School|Institute|Center|Centre|학원))?\b",
    re.IGNORECASE,
) if _KR_ACADEMY_LONG else None

_KR_ACADEMY_RE_SHORT = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in _KR_ACADEMY_SHORT) + r")"
    r"(?:\s+(?:English|Language|Academy|School|Institute|Center|Centre|학원))?\b",
    # 대소문자 구분 — 소문자 "dis", "sei" 등 일반 영어 단어 오탐 방지
) if _KR_ACADEMY_SHORT else None

def _KR_ACADEMY_RE_finditer(line: str):
    results = []
    if _KR_ACADEMY_RE_LONG:
        results.extend(_KR_ACADEMY_RE_LONG.finditer(line))
    if _KR_ACADEMY_RE_SHORT:
        results.extend(_KR_ACADEMY_RE_SHORT.finditer(line))
    return results

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

# 생년월일 독립행 패턴 (이력서에서 bare date로 적힌 경우)
_BARE_DOB_RE = re.compile(
    # "30 Nov 98" / "Nov 30, 1998" / "1998-11-30" / "30/11/1998" / "30.11.1998"
    r"^\s*(?:\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{2,4}"
    r"|\d{1,2}[\/\.\-]\d{1,2}[\/\.\-]\d{2,4}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4})\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# 단독 성별/국적/주소 행 — v2.9 확장: 국가명 단독 줄도 삭제 (이력서 주소 헤더)
_BARE_PERSONAL_RE = re.compile(
    r"^\s*(?:Female|Male|Non-?binary"
    r"|South\s+African|South\s+Korean|Korean|American|British|Canadian|"
    r"Australian|New\s+Zealander|Irish|Filipino|Zimbabwean|Zambian|"
    r"Kenyan|Ghanaian|Nigerian|Ugandan|Tanzanian|Senegalese|Namibian"
    # 국가명 단독 줄 (이력서 주소 필드에서 국가만 표시된 경우)
    r"|South\s+Africa|South\s+Korea|New\s+Zealand|United\s+Kingdom|"
    r"United\s+States(?:\s+of\s+America)?|United\s+Arab\s+Emirates"
    r")\s*$",
    re.IGNORECASE | re.MULTILINE,
)

def _is_year_range(matched: str) -> bool:
    """전화번호처럼 보이는 연도 범위(2017-2021 등) 여부 판별."""
    digits = re.findall(r"\d+", matched)
    return bool(digits) and all(1900 <= int(d) <= 2099 for d in digits)


def _apply_regex(text: str) -> tuple[str, list[PIIMatch]]:
    """regex 패턴으로 PII 감지 + 마스킹."""
    found:   list[PIIMatch] = []

    # ── 제로폭/불가시 유니코드 문자 제거 (CVpop PDF 등에서 발생) ──────────────
    # \u200b(ZERO WIDTH SPACE), \u200c/d(ZW NON-JOINER/JOINER), \u200e/f(LTR/RTL MARK),
    # \ufeff(BOM), \u00ad(SOFT HYPHEN), \u2028/9(LINE/PARA SEP)
    # 이 문자들이 있으면 "Business or sector:", "RISE" 등 정규식 매칭 실패
    _INVIS_RE = re.compile(
        r"[\u200b\u200c\u200d\u200e\u200f\u00ad\ufeff\u2028\u2029]"
    )
    text    = _INVIS_RE.sub("", text)
    cleaned: str = text

    # ── 문서 전체 한국 컨텍스트 사전 판단 (원본 텍스트 기준) ──────────────────
    # addr_kr_en 등이 먼저 치환되면 window 검사에서 context 소실 → 원본으로 먼저 확인
    _doc_has_korea = bool(
        re.search(r"\b(?:South\s+Korea|Korea|한국)\b", text, re.IGNORECASE)
        or _KR_CITY_RE.search(text)
        or re.search(r"[가-힣]", text)
    )

    # ── 기본 패턴 (전화/이메일/주소/SNS) ──────────────────────────────────
    for ptype, pattern in _PATTERNS.items():
        for m in pattern.finditer(cleaned):
            # 전화번호 False Positive: 연도 범위(2017-2021 등) 차단
            if ptype in ("phone_kr", "phone_intl", "phone_us") and _is_year_range(m.group(0)):
                continue
            # addr_kr_en → "South Korea" 직접 대체
            # (마커→빈문자열 경로를 쓰면 "Bundang, South Korea" 같은 인접 줄에서
            #  Korean context 증거가 사라져 has_kr3 계산이 실패하는 버그 방지)
            replacement = "South Korea" if ptype == "addr_kr_en" else f"[{ptype.upper()}_REMOVED]"
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

        # 수정 7/v2.9: 인접 줄(±2) 직접 증거만 — _doc_has_korea 글로벌 폴백 제거
        # (이유: SA/해외 직장이 있는 복합 CV에서 한국 미언급 줄까지 익명화되는 버그 방지)
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
            # 예외: 한국 컨텍스트이고 3단어 이상 기관명 → 고유명사이므로 삭제
            # (예: "Daewon Foreign Language High School" ≠ "High School Teacher")
            if _TITLE_SAFE_RE.search(orig) and not (has_kr_ctx and len(orig.split()) >= 3):
                continue
            # 수정 2: 교육 섹션 내 학위/전공명 삭제 금지
            if in_edu_section:
                continue
            # 수정 7: 해외 기관 보존 (한국 컨텍스트 없으면 스킵)
            if not has_kr_ctx:
                continue
            # 모든 학원/학교명 → "English Academy, South Korea" (University 포함)
            # University는 PRESERVE_INSTITUTION에서 이미 보존됨
            repl = "English Academy, South Korea"
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

    # ── 미국 도시+주 / 외국 도시 — 수정 7: 해외 도시 보존 (비활성화) ───────────
    # RE_US_CITY_STATE, RE_FOREIGN_CITY 비활성화:
    #   - 해외 근무지 도시명(Houston, Calgary, Prague 등)은 보존 대상
    #   - 한국 도시만 수정 4(_KR_CITY_RE)에서 처리
    # (Houston → South Korea, Calgary → South Korea 오작동 방지)

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

    # ── 수정 5/6/7/v2.9: 한국 학원/교육기관 (컨텍스트 확인 + 전체 토큰 교체) ──────
    # v2.9 변경:
    #   - in_edu_section3 추가 → 교육 섹션 내 기관명 보존
    #   - has_kr3 에서 _doc_has_korea 글로벌 폴백 제거 → 인접 줄 직접 증거만 사용
    lines3 = cleaned.split("\n")
    new_lines3 = []
    in_edu_section3 = False
    for i, line in enumerate(lines3):
        # 교육 섹션 헤더 추적 (독립 재추적 — cleaned 기준으로 라인 인덱스 다를 수 있음)
        if _EDU_HDR_RE.match(line):
            in_edu_section3 = True
        elif _NON_EDU_HDR_RE.match(line):
            in_edu_section3 = False

        window3 = " ".join(lines3[max(0, i - 2):i + 3])
        # v2.9: _doc_has_korea 글로벌 폴백 제거 — 인접 줄 직접 증거만
        has_kr3 = bool(
            re.search(r"\b(?:South\s+Korea|Korea|한국)\b", window3, re.IGNORECASE)
            or _KR_CITY_RE.search(window3)
            or re.search(r"[가-힣]", window3)
        )
        has_foreign3 = bool(
            RE_FOREIGN_CITY.search(window3) or RE_US_CITY_STATE.search(window3)
        )

        # KR_ACADEMY_RE: 고유명사 (수정 5/6/7)
        # v3.0 분리 처리:
        #   LONG 브랜드 (4자 초과): 큐레이션된 한국 브랜드 → Korea 컨텍스트 없어도 익명화
        #     (Knox, Chungdahm 등은 한국 외 맥락 없으면 항상 익명화)
        #     예외: 명확한 해외 컨텍스트(해외도시+한국 없음) → 보존
        #   SHORT 약어 (4자 이하): 오탐 위험 → _doc_has_korea 폴백 필요
        _has_kr3_or_doc = has_kr3 or _doc_has_korea

        # LONG 큐레이션 브랜드: 한국 컨텍스트 없어도 익명화 (항상)
        if _KR_ACADEMY_RE_LONG:
            for m in _KR_ACADEMY_RE_LONG.finditer(line):
                orig = m.group(0)
                if in_edu_section3:
                    continue
                # 해외 컨텍스트 명확 + 한국 없음 → 보존 (해외 동명 기관일 수 있음)
                if has_foreign3 and not has_kr3:
                    continue
                if _TITLE_SAFE_RE.search(line) and not has_kr3:
                    continue
                found.append(PIIMatch(
                    type="company",
                    original_value=orig,
                    position=0,
                    confidence=0.90,
                    color="red",
                ))
                line = line.replace(orig, "English Academy, South Korea", 1)

        # SHORT 약어: Korea 컨텍스트 필수 (일반 영어 단어 오탐 방지)
        if _KR_ACADEMY_RE_SHORT:
            for m in _KR_ACADEMY_RE_SHORT.finditer(line):
                orig = m.group(0)
                if in_edu_section3:
                    continue
                if not _has_kr3_or_doc:
                    continue
                if has_foreign3 and not has_kr3:
                    continue
                if _TITLE_SAFE_RE.search(line) and not has_kr3:
                    continue
                found.append(PIIMatch(
                    type="company",
                    original_value=orig,
                    position=0,
                    confidence=0.90,
                    color="red",
                ))
                line = line.replace(orig, "English Academy, South Korea", 1)

        # 일반 KR_WORKPLACE: 한국 컨텍스트 필수 + 교육 섹션 제외 (수정 6/7/v2.9)
        if has_kr3 and not in_edu_section3:
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
                line = line.replace(orig, "English Academy, South Korea", 1)

        new_lines3.append(line)
    cleaned = "\n".join(new_lines3)

    # ── PII 라벨 줄 삭제 (nationality/race/religion/gender/dob 등) ─────────
    cleaned = _PII_LABEL_RE.sub("", cleaned)

    # ── 생년월일 독립행 삭제 ("30 Nov 98" 등) ─────────────────────────────
    for m in _BARE_DOB_RE.finditer(cleaned):
        found.append(PIIMatch(type="dob", original_value=m.group(0).strip(),
                              position=m.start(), confidence=0.95, color="red"))
    cleaned = _BARE_DOB_RE.sub("", cleaned)

    # ── 단독 성별/국적 행 삭제 ("Female" / "South African" 등) ──────────────
    cleaned = _BARE_PERSONAL_RE.sub("", cleaned)

    # ── Reference 섹션 전체 삭제 ──────────────────────────────────────────
    cleaned = remove_reference_section(cleaned)

    # ── 학원/기관명 끝 "Campus" 제거 ─────────────────────────────────────
    # "English Academy South Korea Campus" → "English Academy South Korea"
    # 단순 제거: "Campus of X" 형태는 유지 (of 뒤에 단어 있으면 제거 안 함)
    cleaned = re.sub(r"\s+Campus\b(?!\s+of\b)", "", cleaned, flags=re.IGNORECASE)

    # ── 영문 한국 주소 후처리 ─────────────────────────────────────────────
    # "[ADDR_KR_EN_REMOVED]" → 빈 문자열 ([ \t] 만 — \n은 먹지 않음)
    cleaned = re.sub(r"\[ADDR_KR_EN_REMOVED\][ \t]*,?[ \t]*", "", cleaned)
    # 남은 "{city/dong}, South Korea" 패턴 재검사 (addr_kr_en이 놓친 것)
    cleaned = re.sub(
        r"\b[A-Z][A-Za-z\-]+-(?:dong|gu|si|ro|gil)\b[,\s]*(?:South\s+)?Korea\b",
        "South Korea",
        cleaned,
        flags=re.IGNORECASE,
    )
    # "{동/구명}, Seoul, South Korea" → "South Korea"
    cleaned = re.sub(
        r"\b[A-Z][A-Za-z\-]+,\s*Seoul,?\s*South\s+Korea\b",
        "South Korea",
        cleaned,
        flags=re.IGNORECASE,
    )

    # ── "South Korea (South Korea...)" / "(Republic of Korea)" 중복 정규화 ──
    # PDF 추출 시 생기는 다양한 중복 형태 제거
    # e.g. "South Korea (South Korea (Republic of Korea))"
    cleaned = re.sub(
        r"South\s+Korea\s*\([^)]*(?:South\s+Korea|Republic\s+of\s+Korea)[^)]*\)",
        "South Korea",
        cleaned,
        flags=re.IGNORECASE,
    )
    # e.g. "(South Korea (Republic of Korea))" — addr_kr_en이 앞부분 삭제 후 잔류
    cleaned = re.sub(
        r"\(South\s+Korea\s*\([^)]*Republic\s+of\s+Korea[^)]*\)\)",
        "South Korea",
        cleaned,
        flags=re.IGNORECASE,
    )
    # e.g. "(South Korea)" standalone parenthetical → "South Korea"
    cleaned = re.sub(r"\(South\s+Korea\)", "South Korea", cleaned, flags=re.IGNORECASE)
    # e.g. "(Republic of Korea)" anywhere
    cleaned = re.sub(r"\s*\((?:the\s+)?Republic\s+of\s+Korea\)", "", cleaned, flags=re.IGNORECASE)

    # ── 최종 정리: [TYPE_REMOVED] 마커 제거 ─────────────────────────────────
    # \s 대신 [ \t] 사용 — \n(줄바꿈)을 삼키면 다음 줄과 합쳐지는 버그 방지
    cleaned = re.sub(r"\[[A-Z_]+_REMOVED\][ \t,;:]*", "", cleaned)

    # ── 학원명/기관 뒤 파이프 구분자 + 위치명 정리 ──────────────────────────
    # "English Academy | Dongtan, Mokdong" → "English Academy"
    # "English Academy | South Korea"      → "English Academy"
    # "University | South Korea 2"         → "University"
    # ⚠️ 날짜 범위 보호: "Academy | 2023-2025" → 파이프 뒤가 연도면 제거 금지
    # ⚠️ [ \t]* 사용 필수 — \s*는 \n을 넘어 다음 줄 날짜까지 삭제하는 버그 발생
    cleaned = re.sub(
        # 파이프 뒤가 날짜(19xx-20xx 또는 단독 연도)면 제거 금지
        r"[ \t]*\|[ \t]*(?!\s*(?:19|20)\d{2})[A-Za-z][A-Za-z0-9 \t,\-]*(?=[ \t]*(?:\n|$))",
        "",
        cleaned,
        flags=re.MULTILINE,
    )
    # 파이프 뒤가 빈 경우도 제거: "English Academy | " → "English Academy"
    cleaned = re.sub(r"[ \t]*\|[ \t]*(?=[ \t]*(?:\n|$))", "", cleaned, flags=re.MULTILINE)

    # ── 값 없는 PII 레이블 줄 제거 ───────────────────────────────────────────
    # "Email: " / "Phone: " / "Kakao ID: " 등 값이 제거된 후 레이블만 남은 줄
    cleaned = re.sub(
        r"^[^\n]*\b(?:email|e-mail|phone|telephone|tel|mobile|cell(?:ular)?|"
        r"kakao(?:\s+(?:talk|id))?|카카오|카톡|line\s+id|wechat|"
        r"linkedin|instagram|facebook|twitter|fax|address|주소)\s*:?\s*$",
        "",
        cleaned,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    # ── 커버레터 보일러플레이트 헤더 제거 ─────────────────────────────────────
    # "Application for ESL Teacher Position" / "Cover Letter" 단독 줄
    cleaned = re.sub(
        r"^[^\n]*(?:application\s+for\s+(?:esl\s+)?(?:teacher|teaching|english)\s+"
        r"(?:position|role|post|job)|cover\s+letter\s*:?|curriculum\s+vitae)\s*$",
        "",
        cleaned,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    # ── 이력서 생성 도구 워터마크 제거 ────────────────────────────────────────
    # "Resume created by CVpop - www.cvpop.com" / "Created with Canva" 등
    cleaned = re.sub(
        r"^[^\n]*(?:resume\s+created\s+by|cv\s+created\s+by|created\s+with|"
        r"created\s+using|powered\s+by|generated\s+by|made\s+with)\s*"
        r"[^\n]*(?:cvpop|canva|resume\.io|zety|novoresume|resumegenius|"
        r"kickresume|livecareer|indeed|enhancv|visualcv|flowcv|"
        r"resumebuilder|resumelab|www\.[a-z]+\.com)[^\n]*$",
        "",
        cleaned,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    # "www.cvpop.com" URL만 단독으로 남은 경우도 제거
    cleaned = re.sub(
        r"^[^\n]*www\.[a-z]{3,20}\.com[^\n]*$",
        "",
        cleaned,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    # ── 미등록 업체명 범용 익명화 ──────────────────────────────────────────────
    # "ABC Academy 2019-2022" → "English Academy, South Korea 2019-2022"
    # "XYZ English School" / "Greenfield International School" 등
    # 규칙: 1~4개 Title Case 단어 + Academy/School/Institute/College/Kindergarten/Hagwon
    # 단, 이미 "English Academy, South Korea"인 경우 유지
    _INST_SUFFIX = (
        r"(?:Academy|School|Institute|College|Kindergarten|Hagwon|"
        r"English\s+(?:School|Center|Centre|Institute)|"
        r"Language\s+(?:School|Center|Centre|Institute)|"
        r"Learning\s+(?:Center|Centre)|"
        r"Education(?:\s+(?:Center|Centre|Group|Institute))?)"
    )
    _already_anon = re.compile(r"^english\s+academy(?:,?\s+south\s+korea)?$", re.IGNORECASE)
    _inst_suffix_re = re.compile(
        r"\b([A-Z][A-Za-z0-9\-\'&\.]*(?:[ \t]+[A-Z][A-Za-z0-9\-\'&\.]+){0,3}[ \t]+)" + _INST_SUFFIX + r"\b",
    )
    # v2.9: 라인별 처리 — 교육 섹션 및 해외 컨텍스트 줄은 skip
    # (이유: 글로벌 re.sub는 "CPUT Wellington" 같은 해외 기관도 익명화할 수 있음)
    _inst_lines = cleaned.split("\n")
    _inst_new   = []
    _inst_edu   = False
    for _ii, _ln in enumerate(_inst_lines):
        if _EDU_HDR_RE.match(_ln):
            _inst_edu = True
        elif _NON_EDU_HDR_RE.match(_ln):
            _inst_edu = False
        if _inst_edu:
            _inst_new.append(_ln)
            continue
        # 인접 줄 한국 컨텍스트 필수
        _win = " ".join(_inst_lines[max(0, _ii - 2):_ii + 3])
        _has_kr = bool(
            re.search(r"\b(?:South\s+Korea|Korea|한국)\b", _win, re.IGNORECASE)
            or _KR_CITY_RE.search(_win)
            or re.search(r"[가-힣]", _win)
        )
        if _has_kr:
            _ln = _inst_suffix_re.sub(
                lambda m: m.group(0) if _already_anon.match(m.group(0).strip()) else "English Academy, South Korea",
                _ln,
            )
        _inst_new.append(_ln)
    cleaned = "\n".join(_inst_new)

    # ── 주소 제거 후 잔류 쉼표/구두점 정리 ───────────────────────────────────
    cleaned = re.sub(r",\s*,+", ",", cleaned)
    cleaned = re.sub(r",\s*$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s{3,}", "  ", cleaned)

    # ── 고아 괄호 정리 ────────────────────────────────────────────────────────
    # 단독 ")" 줄만 제거 (다음 줄에서 이어지는 괄호 오인 방지)
    # v3.0: 이전 regex는 "Foreign Language)" 같은 다음줄 이어 괄호도 제거하는 버그
    #   → 변경: ONLY remove if line is JUST ")" (standalone orphan)
    #   → "South Korea)" 같은 짧은 잔류는 South Korea 뒤의 ) 만 제거
    cleaned = re.sub(r"^\s*\)\s*$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"(?<=South Korea)\s*\)(?=\s*$)", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    # 줄 시작 또는 단독 ")" 제거
    cleaned = re.sub(r"^\s*\)\s*$", "", cleaned, flags=re.MULTILINE)

    # ── PDF 템플릿 잔류 레이블 제거 ───────────────────────────────────────────
    # "Personal information" / "ESL teacher" (단독 줄) 같은 CV 템플릿 헤더
    cleaned = re.sub(
        r"^(?:Personal\s+information|Contact\s+information|Contact\s+details|"
        r"Personal\s+details|Basic\s+information|Profile\s+information|"
        r"ESL\s+(?:teacher|instructor)|English\s+teacher|Native\s+speaker|"
        r"Desired\s+job\s+type|Job\s+type|Desired\s+position|Position\s+sought|"
        r"Objective|Career\s+objective|Target\s+role)\s*$",
        "",
        cleaned,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    # ── CV 섹터/업종 라벨 제거 ─────────────────────────────────────────────
    # "Business or sector: English Academy" / "Industry: Education" 등 잔류 라벨
    cleaned = re.sub(
        r"^[^\n]*\b(?:Business\s+or\s+sector|Industry|Sector|Field\s+of\s+work|"
        r"Employment\s+type|Contract\s+type|Job\s+type)\s*:.*$",
        "",
        cleaned,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    # ── 아이콘/기호 전용 줄 제거 (Europass 등 CV 장식 문자) ──────────────────
    # 알파벳·한글·숫자·불릿이 전혀 없는 줄 → 장식 아이콘으로 판단, 제거
    # 불릿(•●▪◦‣⁃∙·) 단독 줄은 목록 구조이므로 보존
    cleaned = re.sub(r"^(?!.*[a-zA-Z가-힣0-9•●▪◦‣⁃∙·])[^\n]*$", "", cleaned, flags=re.MULTILINE)

    # ── 한국 행정구역 접미사 잔류 정리 (-si / -gu / -dong 등) ──────────────────
    # 도시명 제거 후 남은 찌꺼기: "Currently in South Korea, -si," / ", Suwon-si" 등
    cleaned = re.sub(
        r",?\s*-?(?:si|gu|dong|ro|gil|eup|myeon|ri)\b[,.]?\s*",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    # 쉼표 + 공백만 남은 경우 정리: "South Korea, " → "South Korea"
    cleaned = re.sub(r",\s*$", "", cleaned, flags=re.MULTILINE)

    # ── 커버레터 서명 이름 제거 ────────────────────────────────────────────────
    # "Kamo T." / "John D." / "T. Smith" — 이름+이니셜 형태 서명 (문서 끝 부분)
    # 패턴: 대문자 시작 1~2 단어 + 단일 이니셜(대문자+점) 단독 줄
    cleaned = re.sub(
        r"^[A-Z][a-z]{2,12}(?:\s+[A-Z][a-z]{2,12})?\s+[A-Z]\.\s*$",
        "",
        cleaned,
        flags=re.MULTILINE,
    )
    # NOTE: "Yours sincerely," / "Kind regards," 등 결별 인사는 삭제하지 않음
    # → Layer 2(_apply_known_names) 전에 _preserve_closing_firstname 처리로
    #   서명 이름만 첫이름으로 교체됨 (analyze_pii 참조)

    # ── 외국 도시+파이프 조합 제거 ─────────────────────────────────────────────
    # "University of Limpopo | Polokwane" / "Debate Society | Turfloop" 등
    # 파이프 뒤 단어가 남아있는 경우 (파이프 제거 regex가 앞에서 이미 처리하지만
    # 이름 치환 이후 새로 생긴 경우 재처리)
    # ⚠️ 날짜 범위 보호: "Academy | 2023-2025" 제거 금지
    cleaned = re.sub(
        r"[ \t]*\|[ \t]*(?!(?:19|20)\d{2})[A-Z][A-Za-z\-\s]{2,30}(?=[ \t]*(?:\n|$))",
        "",
        cleaned,
        flags=re.MULTILINE,
    )

    # ── "South Korea" 중복 줄 정리 ──────────────────────────────────────────
    # "English Academy, South Korea\nSouth Korea" → 중복 제거
    # (addr_kr_en 치환 후 city 줄이 "South Korea"로 남아 중복 발생)
    cleaned = re.sub(
        r"(English Academy, South Korea)[ \t]*\n[ \t]*South Korea\b[ \t]*(?=\n|$)",
        r"\1",
        cleaned,
        flags=re.IGNORECASE,
    )
    # 독립 "South Korea" 단독 줄이 앞 줄에 이미 "South Korea"가 있으면 제거
    cleaned = re.sub(
        r"(?<=South Korea)\n[ \t]*South Korea[ \t]*(?=\n|$)",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    # ── 연속 빈 줄 정리 (최대 2줄) ───────────────────────────────────────────
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned, found


# ── Layer 2: 이름 정확 매칭 삭제 (구글시트 name 기반) ────────────────────────
# 최소 글자 수: 4자 미만 단독 토큰은 삭제 안 함 (Ann, Jo 등 일반 단어 오탐 방지)
_MIN_NAME_TOKEN_LEN = 4

def _apply_known_names(text: str, known_names: list[str]) -> tuple[str, list[PIIMatch]]:
    """구글시트에서 받은 이름으로 정확 매칭 삭제.

    삭제 범위:
      - 풀네임 전체 (대소문자 무관)
      - 이름(first name, ≥4자)
      - 성(last name, ≥4자)
    중간 이름은 단독 삭제 안 함 (오탐 방지).
    """
    found:   list[PIIMatch] = []
    cleaned: str = text

    for full_name in known_names:
        full_name = full_name.strip()
        if not full_name:
            continue
        parts = full_name.split()

        # 1) 풀네임 전체
        pat = re.compile(re.escape(full_name), re.IGNORECASE)
        for m in pat.finditer(cleaned):
            found.append(PIIMatch("name", m.group(0), m.start(), 0.99, "red"))
        cleaned = pat.sub("", cleaned)

        # 2) first name (index 0, ≥4자)
        if parts and len(parts[0]) >= _MIN_NAME_TOKEN_LEN:
            pat = re.compile(r'\b' + re.escape(parts[0]) + r'\b', re.IGNORECASE)
            for m in pat.finditer(cleaned):
                found.append(PIIMatch("name", m.group(0), m.start(), 0.97, "red"))
            cleaned = pat.sub("", cleaned)

        # 3) last name (last token, ≥4자, first name과 다를 때)
        if len(parts) >= 2 and parts[-1] != parts[0] and len(parts[-1]) >= _MIN_NAME_TOKEN_LEN:
            pat = re.compile(r'\b' + re.escape(parts[-1]) + r'\b', re.IGNORECASE)
            for m in pat.finditer(cleaned):
                found.append(PIIMatch("name", m.group(0), m.start(), 0.97, "red"))
            cleaned = pat.sub("", cleaned)

    return cleaned, found


# ── 커버레터 서명 첫이름 보존 ──────────────────────────────────────────────
_CLOSING_LINE_RE = re.compile(
    r"^(?:Yours\s+(?:truly|sincerely|faithfully)|Kind\s+regards?|Best\s+regards?|"
    r"Warm\s+regards?|Sincerely)[,;.]?\s*$",
    re.IGNORECASE,
)
# Layer 2 이름 삭제에서 살아남기 위한 마커 (Layer 2 regex가 이 문자열을 이름으로 오인하지 않음)
_FIRSTNAME_MARKER = "__BRIDGE_FIRSTNAME__"

def _preserve_closing_firstname(text: str, known_names: list[str]) -> str:
    """커버레터 결별 인사 다음 줄의 풀네임 → 마커로 대체.

    Layer 2(_apply_known_names)가 이름을 삭제하기 전에 마커로 치환.
    Layer 2 이후 analyze_pii에서 마커를 첫이름으로 복원.
    예: "Yours sincerely,\nMichelle Sinikiwe Sibanda" → "Yours sincerely,\n__BRIDGE_FIRSTNAME__"
    """
    lines = text.split("\n")
    prev_was_closing = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if _CLOSING_LINE_RE.match(stripped):
            prev_was_closing = True
            new_lines.append(line)
            continue
        if prev_was_closing:
            for full_name in known_names:
                full_name = full_name.strip()
                if not full_name:
                    continue
                # 이 줄이 풀네임과 정확히 일치하면 → 마커로 대체 (Layer 2 생존)
                if re.fullmatch(re.escape(full_name), stripped, re.IGNORECASE):
                    leading = len(line) - len(line.lstrip())
                    line = line[:leading] + _FIRSTNAME_MARKER
                    break
            prev_was_closing = False
        else:
            prev_was_closing = False
        new_lines.append(line)
    return "\n".join(new_lines)


# ── 메인 함수 ──────────────────────────────────────────────────────────────
def analyze_pii(
    text:        str,
    api_key:     str | None  = None,   # 하위 호환용, 더 이상 사용 안 함
    focus:       bool        = False,  # 하위 호환용, 더 이상 사용 안 함
    known_names: list[str] | None = None,
) -> PIIResult:
    """
    전체 PII 분석 실행.

    Args:
        text:        분석할 텍스트
        api_key:     미사용 (하위 호환 유지)
        focus:       미사용 (하위 호환 유지)
        known_names: 구글시트에서 받은 강사 이름 목록 (정확 매칭 삭제)

    Returns:
        PIIResult
    """
    if not text or not text.strip():
        return PIIResult(cleaned_text=text)

    # Layer 1: regex
    cleaned1, found1 = _apply_regex(text)

    # Layer 1.5: 커버레터 서명 풀네임 → 마커로 치환 (Layer 2 이름 삭제 생존용)
    if known_names:
        cleaned1 = _preserve_closing_firstname(cleaned1, known_names)

    # Layer 2: 구글시트 이름 정확 매칭
    if known_names:
        cleaned2, found2 = _apply_known_names(cleaned1, known_names)
    else:
        cleaned2, found2 = cleaned1, []

    # Layer 2.5: 마커 → 실제 첫이름으로 복원
    if known_names and _FIRSTNAME_MARKER in cleaned2:
        first_name = ""
        for n in known_names:
            parts = n.strip().split()
            if parts:
                first_name = parts[0]
                break
        if first_name:
            cleaned2 = cleaned2.replace(_FIRSTNAME_MARKER, first_name, 1)
        # 혹시 남은 마커 제거
        cleaned2 = cleaned2.replace(_FIRSTNAME_MARKER, "")

    return PIIResult(
        cleaned_text=cleaned2,
        pii_found=found1 + found2,
        uncertain=[],
    )


def analyze_pii_focus(text: str, api_key: str | None = None) -> PIIResult:
    """하위 호환 — analyze_pii 위임."""
    return analyze_pii(text)


# ── 로드 API 키 ────────────────────────────────────────────────────────────
def load_api_key() -> Optional[str]:
    """환경변수 → vault → None 순서로 Anthropic API 키 로드."""
    # 1. 환경변수
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if key:
        return key

    # 2. Q:/Claudework/.vault/anthropic.key (평문 파일)
    vault_path = Path("Q:/Claudework/.vault/anthropic.key")
    if vault_path.exists():
        return vault_path.read_text(encoding="utf-8").strip()

    # 3. Bridge MasterVault (tools/master_vault.py seal로 등록된 경우)
    try:
        import sys as _sys
        _vault_dir = str(Path(__file__).parent.parent)
        if _vault_dir not in _sys.path:
            _sys.path.insert(0, _vault_dir)
        from master_vault import get_secret
        key = get_secret("ANTHROPIC_API_KEY")
        if key:
            return key
    except Exception:
        pass

    # 4. 같은 폴더 .api_key (개발용 로컬 파일)
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
