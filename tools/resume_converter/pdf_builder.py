"""
pdf_builder.py — BRIDGE Resume Converter
PDF 조립 + 압축

구조:
  1페이지: 강사 ID(좌상단) + 증명사진(우상단) + 여백
  2~N: Cover Letter (PII 삭제본)
  N~M: CV/Resume (PII+업체명 삭제본)
  M~:  Recommendation (있는 경우)

파일명: {번호}_{국적}_{성별}({출생년}born).pdf
목표: 300KB 이하
"""

from __future__ import annotations

import io
import logging
import re
import tempfile
from pathlib import Path
from typing import Optional

import pikepdf
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth as _rl_sw
import pdfplumber

# ── 한글 폰트 등록 (맑은 고딕 — 윈도우 기본) ──────────────────────────────
_KOREAN_FONT: str | None = None
_KOREAN_FONT_BOLD: str | None = None

def _init_korean_font() -> None:
    """맑은 고딕(또는 굴림) TTF 등록. 한 번만 실행."""
    global _KOREAN_FONT, _KOREAN_FONT_BOLD
    if _KOREAN_FONT:
        return
    import os
    candidates = [
        ("C:/Windows/Fonts/malgun.ttf",   "C:/Windows/Fonts/malgunbd.ttf"),
        ("C:/Windows/Fonts/gulim.ttc",    "C:/Windows/Fonts/gulim.ttc"),
    ]
    for reg, bold in candidates:
        if os.path.exists(reg):
            try:
                pdfmetrics.registerFont(TTFont("KO", reg))
                _KOREAN_FONT = "KO"
                try:
                    if reg != bold and os.path.exists(bold):
                        pdfmetrics.registerFont(TTFont("KO-Bold", bold))
                        _KOREAN_FONT_BOLD = "KO-Bold"
                    else:
                        _KOREAN_FONT_BOLD = "KO"
                except Exception:
                    _KOREAN_FONT_BOLD = "KO"
                break
            except Exception:
                continue

_init_korean_font()

log = logging.getLogger("pdf_builder")

# ── 파일명 생성 ────────────────────────────────────────────────────────────
_GENDER_MAP = {
    "male": "남성", "female": "여성", "m": "남성", "f": "여성",
    "남": "남성", "여": "여성", "남성": "남성", "여성": "여성",
}
_NAT_MAP = {
    # 국가명 (country name)
    "usa": "미국", "us": "미국", "united states": "미국", "united states of america": "미국",
    "canada": "캐나다",
    "uk": "영국", "united kingdom": "영국", "great britain": "영국", "england": "영국",
    "australia": "호주",
    "new zealand": "뉴질랜드", "nz": "뉴질랜드",
    "south africa": "남아공",
    "ireland": "아일랜드",
    "philippines": "필리핀",
    "zimbabwe": "짐바브웨",
    "nigeria": "나이지리아",
    "ghana": "가나",
    "jamaica": "자메이카",
    "kenya": "케냐",
    # 국적 형용사 (nationality adjective)
    "american": "미국", "canadian": "캐나다",
    "british": "영국", "english": "영국", "scottish": "영국", "welsh": "영국",
    "australian": "호주",
    "new zealander": "뉴질랜드", "kiwi": "뉴질랜드",
    "south african": "남아공",
    "irish": "아일랜드",
    "filipino": "필리핀", "philippine": "필리핀",
    "zimbabwean": "짐바브웨",
    "nigerian": "나이지리아",
    "ghanaian": "가나",
    "jamaican": "자메이카",
    "kenyan": "케냐",
}

def build_filename(
    candidate_id: str,
    nationality: str = "",
    gender: str = "",
    birth_year: str = "",
) -> str:
    """
    예: 3126_영국_여성(99born).pdf
    """
    nat = _NAT_MAP.get(nationality.strip().lower(), nationality.strip()) or "미상"
    gen = _GENDER_MAP.get(gender.strip().lower(), gender.strip()) or "미상"
    yr  = str(birth_year)[-2:] if birth_year else "00"
    return f"{candidate_id}_{nat}_{gen}({yr}born).pdf"


# ── 사진 오버레이 유틸 ────────────────────────────────────────────────────────
def _draw_photo_and_id(
    c,
    candidate_id:  str,
    photo_bytes:   bytes | None,
    page_w:        float,
    page_h:        float,
    margin:        float,
    location_hint: str = "",
) -> float:
    """
    첫 페이지 우상단에 사진 + 좌상단에 ID 번호를 그린다.
    location_hint 제공 시 ID 아래에 작게 표시.
    반환값: 사진 하단 y좌표 (본문 시작 y 계산에 사용).
    """
    import os

    # 사진 크기 (증명사진 비율 35mm × 45mm 기준)
    PHOTO_W = 3.2 * cm
    PHOTO_H = 4.2 * cm
    img_x = page_w - margin - PHOTO_W
    img_y = page_h - margin - PHOTO_H

    if photo_bytes:
        try:
            img = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
            # portrait crop: 가로가 더 넓으면 중앙 crop
            w, h = img.size
            if w > h:
                delta = (w - h) // 2
                img = img.crop((delta, 0, w - delta, h))
            # 증명사진 크기: 200×267 px (35mm×45mm @ 150dpi 근사)
            img = img.resize((200, 267), Image.LANCZOS)

            tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            img.save(tmp.name, format="JPEG", quality=80, dpi=(150, 150))
            tmp.close()

            c.drawImage(tmp.name, img_x, img_y,
                        width=PHOTO_W, height=PHOTO_H,
                        preserveAspectRatio=True, mask="auto")
            os.unlink(tmp.name)
        except Exception as e:
            log.warning(f"사진 삽입 실패: {e}")

    # ID 번호 (좌상단 — 강조)
    c.setFont("Helvetica-Bold", 28)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(margin, page_h - margin - 0.9 * cm, f"#{candidate_id}")

    # 위치 힌트 (ID 아래 — 작게)
    if location_hint:
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0.45, 0.45, 0.45)
        c.drawString(margin, page_h - margin - 1.6 * cm, location_hint)

    c.setFillColorRGB(0, 0, 0)

    # 구분선 (사진 하단 기준)
    line_y = img_y - 0.3 * cm
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.setLineWidth(0.5)
    c.line(margin, line_y, page_w - margin, line_y)
    c.setStrokeColorRGB(0, 0, 0)

    return line_y


# ── 텍스트 → PDF 변환 ──────────────────────────────────────────────────────
def text_to_pdf_bytes(
    text:          str,
    title:         str = "",
    line_h:        float = 16,
    margin_cm:     float = 1.5,
    font_size:     int   = 10,
    photo_bytes:   bytes | None = None,
    candidate_id:  str   = "",
) -> bytes:
    """plain text → PDF bytes (reportlab, 한글 지원).

    photo_bytes/candidate_id 제공 시 1페이지 우상단에 사진 + 좌상단에 ID 표시.
    별도 커버 페이지 없이 바로 본문 시작.
    """
    buf    = io.BytesIO()
    page_w, page_h = A4
    c      = rl_canvas.Canvas(buf, pagesize=A4)
    margin = margin_cm * cm
    max_w  = page_w - margin * 2

    body_font = _KOREAN_FONT      if _KOREAN_FONT      else "Helvetica"
    bold_font = _KOREAN_FONT_BOLD if _KOREAN_FONT_BOLD else "Helvetica-Bold"

    def _sw(s: str, fn: str, fs: int) -> float:
        """reportlab stringWidth — 실제 렌더 폭(pt) 반환."""
        try:
            return _rl_sw(s, fn, fs)
        except Exception:
            # 폴백: ASCII 0.6em, CJK 1em
            return sum(fs * (1.0 if ord(ch) > 0x2E7F else 0.6) for ch in s)

    def _wrap(line: str, fn: str, fs: int) -> list[str]:
        """단어 단위 줄바꿈. max_w 초과 시 여러 줄로 분할."""
        if _sw(line, fn, fs) <= max_w:
            return [line]
        words = line.split(" ")
        result, cur = [], ""
        for w in words:
            test = (cur + " " + w).lstrip() if cur else w
            if _sw(test, fn, fs) <= max_w:
                cur = test
            else:
                if cur:
                    result.append(cur)
                # 단어 자체가 너무 길면 강제 분할
                if _sw(w, fn, fs) > max_w:
                    while w:
                        for i in range(len(w), 0, -1):
                            if _sw(w[:i], fn, fs) <= max_w:
                                result.append(w[:i])
                                w = w[i:]
                                break
                        else:
                            result.append(w)
                            w = ""
                else:
                    cur = w
        if cur:
            result.append(cur)
        return result or [""]

    def _new_page() -> float:
        c.showPage()
        c.setFont(body_font, font_size)
        return page_h - margin

    # 섹션 헤더 감지 패턴 (볼드 처리용)
    _HDR_RE = re.compile(
        r"^(?:Summary|Professional\s+experience|Education\s+and\s+training|"
        r"Skills?|Languages?|Certifications?|Achievements?|References?|"
        r"Profile|Career\s+objective|Qualifications?|[A-Z][A-Z\s&/\-]{3,})\s*$"
    )

    # 직업 날짜 범위 감지 패턴 — 새 경력 항목 앞 여백 삽입용
    # "28 Feb 19 - 28 Feb 20" / "4 Sep 23 - 10 Sep 24" / "2019 - 2022" / "Feb 2019 - Mar 2021"
    _DATE_RANGE_RE = re.compile(
        r"^\s*(?:\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{2,4}"
        r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}"
        r"|\d{4})\s*[-–—]\s*"
        r"(?:\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{2,4}"
        r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}"
        r"|\d{4}|present|current|now)\b",
        re.IGNORECASE,
    )

    # ── 텍스트 전처리: 이름/아이콘/중복 헤더 제거 + 위치 힌트 추출 ──────────────
    # 1) 아이콘·기호만 있는 줄 제거 (Europass CV 장식 문자 등)
    text = re.sub(r"^(?!.*[a-zA-Z가-힣0-9])[^\n]*$", "", text, flags=re.MULTILINE)
    # 2) "Currently in South Korea" 추출 → ID 아래 표시용, 본문에서 제거
    _LOC_RE = re.compile(
        r"^[^\n]*(?:currently\s+(?:in|based\s+in|living\s+in)\s+(?:South\s+)?Korea"
        r"|(?:South\s+)?Korea[^\n]*currently)[^\n]*$",
        re.IGNORECASE | re.MULTILINE,
    )
    _location_hint = ""
    _loc_m = _LOC_RE.search(text)
    if _loc_m:
        _raw_loc = _loc_m.group(0).strip()
        # 짧으면 그대로, 길면 "Currently in South Korea" 로 정규화
        if len(_raw_loc) <= 40:
            _location_hint = _raw_loc
        else:
            _location_hint = "Currently in South Korea"
        text = text[:_loc_m.start()] + text[_loc_m.end():]
    # 3) 문서 첫 15줄 안의 이름 단독 줄 제거
    #    (영문 1~3단어, 대문자 시작, 문장부호·동사 없음 → 이름으로 판단)
    _NAME_LINE_RE = re.compile(
        r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\s*$"
    )
    _head = text.split("\n")
    _first_hdr = next(
        (i for i, l in enumerate(_head) if re.match(
            r"^\s*(?:Summary|Profile|Professional|Work|Education|Skills|Certifications|"
            r"Achievements|Languages|References|EXPERIENCE|EDUCATION)", l, re.IGNORECASE
        )), 15
    )
    for _k in range(min(_first_hdr, 15, len(_head))):
        if _NAME_LINE_RE.match(_head[_k].strip()):
            _head[_k] = ""
    text = "\n".join(_head)
    # 4) 정리 후 연속 빈 줄 3개 이상 → 2개로
    text = re.sub(r"\n{3,}", "\n\n", text)

    c.setFont(body_font, font_size)

    # 1페이지: 사진+ID 삽입
    if photo_bytes or candidate_id:
        content_start_y = _draw_photo_and_id(
            c, candidate_id, photo_bytes, page_w, page_h, margin,
            location_hint=_location_hint,
        )
        y = content_start_y - line_h * 0.5
    elif title:
        c.setFont(bold_font, font_size + 1)
        c.drawString(margin, page_h - margin, title)
        c.setFont(body_font, font_size)
        y = page_h - margin - line_h * 1.5
    else:
        y = page_h - margin

    # 빈 줄 연속 최대 1개로 제한
    raw_lines = text.split("\n")
    lines: list[str] = []
    blank = 0
    for ln in raw_lines:
        if ln.strip() == "":
            blank += 1
            if blank <= 1:
                lines.append("")
        else:
            blank = 0
            lines.append(ln)

    # ── 직업 항목 앞 자동 여백 마킹 ─────────────────────────────────────────
    # 날짜 범위 줄 위에서 가장 높은(첫 번째) 비어있지 않은 줄(직책명)에만 마킹.
    # 이전 방식(3줄 모두 마킹)은 직업 내부에 불필요한 간격이 생기는 부작용이 있었음.
    _extra_space: set[int] = set()
    for _i, _ln in enumerate(lines):
        if _DATE_RANGE_RE.match(_ln.strip()):
            # 날짜 줄 위로 최대 3개 비어있지 않은 줄을 탐색 → 가장 위 줄만 마킹
            _j = _i - 1
            _last_non_empty = -1
            _steps = 0
            while _j >= 0 and _steps < 2:
                if lines[_j].strip():
                    _last_non_empty = _j   # 계속 갱신 → 2번째 비어있지 않은 줄 = 직책명
                    _steps += 1
                _j -= 1
            if _last_non_empty >= 0:
                _extra_space.add(_last_non_empty)

    for _idx, raw_line in enumerate(lines):
        stripped = raw_line.strip()

        # 빈 줄 처리
        if stripped == "":
            y -= line_h * 0.65
            if y < margin:
                y = _new_page()
            continue

        # 직업 항목 앞 자동 여백 (날짜 범위 앞 1~2줄 포함)
        if _idx in _extra_space and _idx > 0:
            y -= line_h * 1.5   # ← 직업간 구분 여백 (0.85 → 1.5)
            if y < margin:
                y = _new_page()

        # 헤더 여부 판단
        is_hdr = bool(_HDR_RE.match(stripped))
        fn = bold_font if is_hdr else body_font
        fs = font_size + 1 if is_hdr else font_size
        lh = line_h * 1.3 if is_hdr else line_h

        if is_hdr:
            y -= line_h * 1.0  # 섹션 헤더 앞 여백 (Summary 뒤 Professional experience 등)

        c.setFont(fn, fs)
        for display in _wrap(raw_line.rstrip(), fn, fs):
            if y < margin:
                y = _new_page()
                c.setFont(fn, fs)
            c.drawString(margin, y, display)
            y -= lh

    c.save()
    return buf.getvalue()


# ── 커버레터 1페이지 압축 ───────────────────────────────────────────────────
def _compress_cover_to_1page(text: str, photo_bytes: bytes | None = None, candidate_id: str = "") -> bytes:
    """커버레터가 1페이지 초과 시 단계적 압축. 최대 1페이지."""
    attempts = [
        {"line_h": 16,   "margin_cm": 1.5, "font_size": 11},
        {"line_h": 14,   "margin_cm": 1.5, "font_size": 11},
        {"line_h": 14,   "margin_cm": 1.2, "font_size": 11},
        {"line_h": 13.6, "margin_cm": 1.0, "font_size": 10},
    ]
    for kw in attempts:
        pdf_bytes = text_to_pdf_bytes(text, photo_bytes=photo_bytes, candidate_id=candidate_id, **kw)
        try:
            with pikepdf.Pdf.open(io.BytesIO(pdf_bytes)) as p:
                if len(p.pages) <= 1:
                    return pdf_bytes
        except Exception:
            return pdf_bytes
    return pdf_bytes  # 최소 설정으로 그냥 반환


# ── PDF 에서 텍스트 추출 ───────────────────────────────────────────────────
def _extract_page_column_aware(page) -> str:
    """PyMuPDF page → text (두 컬럼 레이아웃 감지 후 좌→우 순서로 정렬).

    두 컬럼 PDF (예: ABOUT ME | WORK EXPERIENCE 나란히 배치) 에서
    PyMuPDF get_text("text")는 좌/우 줄이 인터리브 되는 문제가 있음.
    block 좌표 기반으로 좌 컬럼 전체 → 우 컬럼 전체 순서로 재정렬.
    """
    blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
    text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]

    if not text_blocks:
        return page.get_text("text")

    page_width = page.rect.width
    page_mid   = page_width / 2

    def _cx(b: tuple) -> float:
        return (b[0] + b[2]) / 2  # block center-x

    # 컬럼 분류: center-x 기준 ±15% 여유
    left_blocks  = [b for b in text_blocks if _cx(b) < page_mid * 0.85]
    right_blocks = [b for b in text_blocks if _cx(b) > page_mid * 1.15]
    full_blocks  = [b for b in text_blocks
                    if b not in left_blocks and b not in right_blocks]

    is_two_col = len(left_blocks) >= 3 and len(right_blocks) >= 3

    if is_two_col:
        # 각 그룹을 y 순서(위→아래)로 정렬
        full_blocks.sort(key=lambda b: b[1])
        left_blocks.sort(key=lambda b: b[1])
        right_blocks.sort(key=lambda b: b[1])
        # 전체폭 헤더 → 좌 컬럼 → 우 컬럼 순서로 출력
        ordered = full_blocks + left_blocks + right_blocks
    else:
        # 단일 컬럼: y → x 순서
        text_blocks.sort(key=lambda b: (b[1], b[0]))
        ordered = text_blocks

    return "\n".join(b[4].strip() for b in ordered if b[4].strip())


def extract_text_from_pdf(pdf_path: Path) -> str:
    """PyMuPDF 우선 텍스트 추출 (두 컬럼 레이아웃 지원 + CID 처리), pdfplumber 폴백."""
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        pages = []
        for p in doc:
            page_text = _extract_page_column_aware(p)
            if not page_text:
                page_text = p.get_text("text")
            pages.append(page_text)
        doc.close()
        text = "\n".join(pages)
        if text.strip():
            return text
    except Exception as e:
        log.debug(f"PyMuPDF 추출 실패 → pdfplumber 폴백: {e}")

    # pdfplumber 폴백
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception as e:
        log.warning(f"PDF 텍스트 추출 실패: {e}")
        return ""


# ── 이미지 압축 ────────────────────────────────────────────────────────────
def _compress_image(img: Image.Image, max_dpi: int = 150) -> bytes:
    buf = io.BytesIO()
    rgb = img.convert("RGB")
    rgb.save(buf, format="JPEG", quality=75, dpi=(max_dpi, max_dpi))
    return buf.getvalue()


# ── 첫 페이지 자동 줄간격 계산 ────────────────────────────────────────────
def _auto_line_h(
    text: str,
    font_size: int = 10,
    margin_cm: float = 1.5,
    has_photo: bool = True,
) -> float:
    """텍스트가 첫 페이지의 ~82%를 채우도록 line_h 자동 계산.
    반환 범위: 16 ~ 26 pt.
    """
    page_w, page_h = A4
    margin = margin_cm * cm
    max_w = page_w - margin * 2

    body_font = _KOREAN_FONT      if _KOREAN_FONT      else "Helvetica"
    bold_font = _KOREAN_FONT_BOLD if _KOREAN_FONT_BOLD else "Helvetica-Bold"

    def _sw2(s: str, fn: str, fs: int) -> float:
        try:
            return _rl_sw(s, fn, fs)
        except Exception:
            return sum(fs * (1.0 if ord(ch) > 0x2E7F else 0.6) for ch in s)

    def _wrap2(line: str, fn: str, fs: int) -> list:
        if _sw2(line, fn, fs) <= max_w:
            return [line]
        words = line.split(" ")
        result, cur = [], ""
        for w in words:
            test = (cur + " " + w).lstrip() if cur else w
            if _sw2(test, fn, fs) <= max_w:
                cur = test
            else:
                if cur:
                    result.append(cur)
                if _sw2(w, fn, fs) > max_w:
                    while w:
                        for i in range(len(w), 0, -1):
                            if _sw2(w[:i], fn, fs) <= max_w:
                                result.append(w[:i])
                                w = w[i:]
                                break
                        else:
                            result.append(w)
                            w = ""
                else:
                    cur = w
        if cur:
            result.append(cur)
        return result or [""]

    # 사용 가능 높이 계산
    if has_photo:
        PHOTO_H = 4.2 * cm
        content_start_y = page_h - margin - PHOTO_H - 0.3 * cm - 8.0
    else:
        content_start_y = page_h - margin
    avail_h = content_start_y - margin

    _HDR_RE2 = re.compile(
        r"^(?:Summary|Professional\s+experience|Education\s+and\s+training|"
        r"Skills?|Languages?|Certifications?|Achievements?|References?|"
        r"Profile|Career\s+objective|Qualifications?|[A-Z][A-Z\s&/\-]{3,})\s*$"
    )

    # 빈 줄 정규화
    raw_lines = text.split("\n")
    lines: list = []
    blank = 0
    for ln in raw_lines:
        if ln.strip() == "":
            blank += 1
            if blank <= 1:
                lines.append("")
        else:
            blank = 0
            lines.append(ln)

    # 총 line units 계산 (blank=0.65, header_pre=0.3, header_lh=1.3, normal=1.0)
    total_units = 0.0
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped == "":
            total_units += 0.65
            continue
        is_hdr = bool(_HDR_RE2.match(stripped))
        fn = bold_font if is_hdr else body_font
        fs = font_size + 1 if is_hdr else font_size
        lh_mult = 1.3 if is_hdr else 1.0
        if is_hdr:
            total_units += 0.3
        wrapped = _wrap2(raw_line.rstrip(), fn, fs)
        total_units += len(wrapped) * lh_mult

    if total_units <= 0:
        return 18.0

    target_h = avail_h * 0.82
    line_h = target_h / total_units
    return max(16.0, min(26.0, line_h))


# ── 메인 빌드 함수 ──────────────────────────────────────────────────────────
def build_pdf(
    candidate_id:  str,
    nationality:   str = "",
    gender:        str = "",
    birth_year:    str = "",
    photo_bytes:   bytes | None = None,
    cover_text:    str | None   = None,
    resume_text:   str | None   = None,
    rec_text:      str | None   = None,
    extra_pdfs:    list[Path]   = [],
    out_dir:       Path | None  = None,
) -> tuple[Path, int]:
    """
    PDF 조립 + 압축.

    Returns:
        (output_path, file_size_bytes)
    """
    page_w, page_h = A4
    pdf_parts: list[bytes] = []

    # ── 1페이지: 커버 없이 바로 본문 시작 (사진+ID는 첫 내용 페이지 우상단) ──
    # 첫 콘텐츠를 결정: 커버레터 > 이력서 순
    _first_added = False

    if cover_text and cover_text.strip():
        # 커버레터 첫 페이지에 사진+ID 삽입 — 줄간격 자동 계산
        _cover_lh = _auto_line_h(cover_text, font_size=10, margin_cm=1.5, has_photo=True)
        pdf_parts.append(text_to_pdf_bytes(
            cover_text,
            photo_bytes=photo_bytes,
            candidate_id=str(candidate_id),
            line_h=_cover_lh,
            margin_cm=1.5,
            font_size=10,
        ))
        _first_added = True

    if resume_text and resume_text.strip():
        if not _first_added:
            # 커버레터 없을 때 이력서 첫 페이지에 사진+ID 삽입 — 줄간격 자동 계산
            _resume_lh = _auto_line_h(resume_text, font_size=10, margin_cm=1.5, has_photo=True)
            pdf_parts.append(text_to_pdf_bytes(
                resume_text,
                photo_bytes=photo_bytes,
                candidate_id=str(candidate_id),
                line_h=_resume_lh,
                margin_cm=1.5,
                font_size=10,
            ))
        else:
            pdf_parts.append(text_to_pdf_bytes(resume_text, line_h=16, font_size=10))
        _first_added = True

    if rec_text and rec_text.strip():
        pdf_parts.append(text_to_pdf_bytes(rec_text, line_h=16, font_size=10))

    # ── 추가 PDF 병합 ──────────────────────────────────────────────────
    for ep in extra_pdfs:
        if ep.exists() and ep.suffix.lower() == ".pdf":
            try:
                pdf_parts.append(ep.read_bytes())
            except Exception as e:
                log.warning(f"추가 PDF 읽기 실패 {ep}: {e}")

    # ── pikepdf 병합 + 압축 + 메타 삭제 ─────────────────────────────────
    merged = pikepdf.Pdf.new()

    for part_bytes in pdf_parts:
        try:
            part_pdf = pikepdf.Pdf.open(io.BytesIO(part_bytes))
            merged.pages.extend(part_pdf.pages)
        except Exception as e:
            log.warning(f"PDF 파트 병합 실패: {e}")

    # 메타데이터 삭제 (docinfo 방식)
    try:
        docinfo = merged.docinfo
        for key in ["/Author", "/Creator", "/Producer", "/Subject", "/Title", "/Keywords"]:
            try:
                if key in docinfo:
                    del docinfo[key]
            except Exception:
                pass
    except Exception as e:
        log.debug(f"메타데이터 삭제 무시: {e}")

    # 압축 저장
    out_buf = io.BytesIO()
    merged.save(
        out_buf,
        compress_streams=True,
        object_stream_mode=pikepdf.ObjectStreamMode.generate,
        stream_decode_level=pikepdf.StreamDecodeLevel.specialized,
    )
    final_bytes = out_buf.getvalue()

    # ── 파일명 + 저장 ────────────────────────────────────────────────────
    fname  = build_filename(candidate_id, nationality, gender, birth_year)
    if out_dir is None:
        out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / fname
    out_path.write_bytes(final_bytes)

    size = len(final_bytes)
    log.info(f"PDF 생성: {fname} ({size//1024}KB, {len(merged.pages)}페이지)")

    if size > 300 * 1024:
        log.warning(f"목표 300KB 초과: {size//1024}KB")

    return out_path, size


# ── CLI ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 테스트
    sample_text = "Hello, I am applying for an ESL teacher position.\n" * 20
    path, sz = build_pdf(
        candidate_id="3126",
        nationality="미국",
        gender="여성",
        birth_year="1999",
        cover_text=sample_text,
        resume_text=sample_text * 2,
    )
    print(f"생성: {path.name} ({sz//1024}KB)")
