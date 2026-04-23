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
            img.save(tmp.name, format="JPEG", quality=72, optimize=True, dpi=(120, 120))
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
    #    불릿(•●▪◦‣⁃∙·) 단독 줄은 목록 구조이므로 보존
    text = re.sub(r"^(?!.*[a-zA-Z가-힣0-9•●▪◦‣⁃∙·])[^\n]*$", "", text, flags=re.MULTILINE)
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
    # 4-b) 2-col 마커가 같은 줄에 붙었거나 공백과 섞였을 경우 전용 줄로 분리
    for _marker in (COL_START, COL_BREAK, COL_END):
        text = text.replace(_marker, f"\n{_marker}\n")
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

    # ── 2-column 섹션 분할 ─────────────────────────────────────────────────
    # 마커로 감싼 구간을 {"type":"2col", "L":[...], "R":[...]}, 그 외는 {"type":"full", "lines":[...]}
    sections: list[dict] = []
    cur: list[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip() == COL_START:
            # FULL 섹션 flush
            if cur:
                sections.append({"type": "full", "lines": cur})
                cur = []
            L: list[str] = []
            R: list[str] = []
            bucket = L
            i += 1
            while i < len(lines):
                t = lines[i]
                if t.strip() == COL_BREAK:
                    bucket = R
                    i += 1
                    continue
                if t.strip() == COL_END:
                    i += 1
                    break
                bucket.append(t)
                i += 1
            sections.append({"type": "2col", "L": L, "R": R})
            continue
        cur.append(ln)
        i += 1
    if cur:
        sections.append({"type": "full", "lines": cur})

    # "Knox Academy | 2023-2025" 형식 (이름 뒤 파이프 + 날짜)
    _PIPED_DATE_RE = re.compile(
        r"\|\s*(?:\d{4}\s*[-–—]\s*(?:\d{4}|present|current|now)|"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4})",
        re.IGNORECASE,
    )

    # ── 렌더 헬퍼 ───────────────────────────────────────────────────────────
    def _reorder_jobtitle(ls: list[str]) -> list[str]:
        """JobTitle\\nCompany|Date 패턴 → Company|Date\\nJobTitle 로 교정.

        재정렬 조건 (is_jobtitle_candidate):
          - 짧은 줄 (단어 7개 이하)
          - 날짜 형식 아님
          - 섹션 타이틀 아님
          - 문장부호(.,;:!) 미종료
          - 다음 비-빈 줄이 날짜 형식
        """
        out: list[str] = []
        i = 0
        while i < len(ls):
            stripped = ls[i].strip()
            nj = i + 1
            while nj < len(ls) and not ls[nj].strip():
                nj += 1
            is_cand = (
                stripped
                and not _SECTION_TITLE_RE.match(stripped)
                and not _DATE_RANGE_RE.match(stripped)
                and not _PIPED_DATE_RE.search(stripped)
                and not stripped.endswith((".", ",", ";", ":", "!"))
                and len(stripped.split()) <= 7
                and nj < len(ls)
                and (
                    _PIPED_DATE_RE.search(ls[nj].strip())
                    or _DATE_RANGE_RE.match(ls[nj].strip())
                )
            )
            if is_cand:
                out.append(ls[nj])   # Company|Date 먼저
                out.append(ls[i])    # Job Title 다음
                i = nj + 1
            else:
                out.append(ls[i])
                i += 1
        return out

    def _compute_extra_space(ls: list[str]) -> set[int]:
        """날짜 줄 바로 다음(line+1)의 짧은 직책명을 jobtitle로 마킹.

        _reorder_jobtitle() 이후 기준:
          Company|Date  ← is_dateline (볼드)
          JobTitle      ← is_jobtitle (일반 폰트, 이 함수로 마킹)
          bullets...

        제외 조건:
          - 섹션 타이틀, 날짜, 문장부호 종료, 8단어 초과
        """
        s: set[int] = set()
        for _i, _ln in enumerate(ls):
            st = _ln.strip()
            is_date = bool(_DATE_RANGE_RE.match(st) or _PIPED_DATE_RE.search(st))
            if not is_date:
                continue
            nj = _i + 1
            while nj < len(ls) and not ls[nj].strip():
                nj += 1
            if nj >= len(ls):
                continue
            nxt = ls[nj].strip()
            if (
                _SECTION_TITLE_RE.match(nxt)
                or _DATE_RANGE_RE.match(nxt)
                or _PIPED_DATE_RE.search(nxt)
                or nxt.endswith((".", ",", ";", ":", "!"))
                or len(nxt.split()) > 7
            ):
                continue
            s.add(nj)
        return s

    def _wrap_w(line: str, fn: str, fs: int, width: float) -> list[str]:
        """단어 단위 줄바꿈 (임의 폭 지원)."""
        if _sw(line, fn, fs) <= width:
            return [line]
        words = line.split(" ")
        result, cur_ = [], ""
        for w in words:
            test = (cur_ + " " + w).lstrip() if cur_ else w
            if _sw(test, fn, fs) <= width:
                cur_ = test
            else:
                if cur_:
                    result.append(cur_)
                if _sw(w, fn, fs) > width:
                    while w:
                        for k in range(len(w), 0, -1):
                            if _sw(w[:k], fn, fs) <= width:
                                result.append(w[:k])
                                w = w[k:]
                                break
                        else:
                            result.append(w)
                            w = ""
                else:
                    cur_ = w
        if cur_:
            result.append(cur_)
        return result or [""]

    # ALL CAPS 섹션 타이틀 (PROFESSIONAL EXPERIENCES, EDUCATION, SKILLS 등)
    _SECTION_TITLE_RE = re.compile(
        r"^(?:Summary|Professional\s+experience|Education\s+and\s+training|"
        r"Skills?|Languages?|Certifications?|Achievements?|References?|"
        r"Profile|Career\s+objective|Qualifications?|[A-Z][A-Z\s&/\-]{3,})\s*$"
    )
    # 날짜 범위가 포함된 줄 (Knox Academy | 2023-2025 등)
    _JOB_DATELINE_RE = re.compile(
        r"(?:\d{4}\s*[-–—]\s*(?:\d{4}|present|current|now)|"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4})",
        re.IGNORECASE,
    )

    def _render_lines(
        ls: list[str],
        x0: float,
        width: float,
        y_start: float,
        lh_local: float,
        allow_page_break: bool = True,
    ) -> float:
        """주어진 column 영역(x0, width)에 lines 렌더. 최종 y 반환."""
        y_ = y_start
        ls = _reorder_jobtitle(ls)        # Company|Date → JobTitle 순서 교정
        extra = _compute_extra_space(ls)  # 교정 후 기준으로 jobtitle 마킹
        for _idx, raw_line in enumerate(ls):
            stripped = raw_line.strip()
            if stripped == "":
                # A구역: job 사이 빈줄 여백 0.65→0.35 (절반 압축)
                y_ -= lh_local * 0.35
                if allow_page_break and y_ < margin:
                    c.showPage()
                    c.setFont(body_font, font_size)
                    y_ = page_h - margin
                continue

            # 타이틀 분류
            is_section  = bool(_SECTION_TITLE_RE.match(stripped))
            is_jobtitle = (_idx in extra)         # 날짜 줄 위 직책명
            is_dateline = bool(_DATE_RANGE_RE.match(stripped)) or bool(_PIPED_DATE_RE.search(stripped))

            # 여백 먼저
            if is_section and _idx > 0:
                y_ -= lh_local * 1.0   # 섹션 제목 앞 (PROFESSIONAL EXPERIENCES 등)
            elif is_dateline and _idx > 0:
                # Company|Date 앞 — 새 직장 구분 (A구역: 여유 간격)
                y_ -= lh_local * 0.85
            elif is_jobtitle and _idx > 0:
                # Job Title — Company|Date 바로 다음, 추가 여백 없음
                y_ -= lh_local * 0.05
            if allow_page_break and y_ < margin:
                c.showPage()
                c.setFont(body_font, font_size)
                y_ = page_h - margin

            # 폰트/크기 결정
            if is_section:
                fn, fs, lh2 = bold_font, font_size + 3, lh_local * 1.3
            elif is_dateline:
                fn, fs, lh2 = bold_font, font_size + 1, lh_local * 1.1  # Company|Date: 볼드
            elif is_jobtitle:
                fn, fs, lh2 = body_font, font_size, lh_local * 1.0      # Job Title: 일반 폰트
            else:
                fn, fs, lh2 = body_font, font_size, lh_local

            c.setFont(fn, fs)
            for display in _wrap_w(raw_line.rstrip(), fn, fs, width):
                if allow_page_break and y_ < margin:
                    c.showPage()
                    c.setFont(fn, fs)
                    y_ = page_h - margin
                if y_ < margin:
                    break
                c.drawString(x0, y_, display)
                y_ -= lh2
        return y_

    # ── 각 섹션 렌더 ───────────────────────────────────────────────────────
    COL_GAP = 0.8 * cm
    col_w   = (max_w - COL_GAP) / 2

    for sec in sections:
        if sec["type"] == "full":
            y = _render_lines(sec["lines"], margin, max_w, y, line_h, allow_page_break=True)
        else:
            # 한쪽이 비었으면 full 로 다운그레이드
            has_L_content = any(s.strip() for s in sec["L"])
            has_R_content = any(s.strip() for s in sec["R"])
            if not (has_L_content and has_R_content):
                merged = [s for s in sec["L"] + sec["R"] if s.strip()]
                y = _render_lines(merged, margin, max_w, y, line_h, allow_page_break=True)
                continue
            # 2-col: 좌/우 동일 y_start 부터 병렬 렌더. 페이지 break 없이 한 페이지에 맞춤.
            # 남은 페이지 공간이 부족하면 먼저 새 페이지로.
            y_top = y

            # 필요 높이 추정 (간이): 각 컬럼의 wrapped 라인 수 × lh
            def _estimate_h(ls, width):
                total = 0.0
                for ln in ls:
                    s = ln.strip()
                    if not s:
                        total += line_h * 0.65
                        continue
                    is_hdr = bool(_HDR_RE.match(s))
                    fn = bold_font if is_hdr else body_font
                    fs = font_size + 1 if is_hdr else font_size
                    lhm = line_h * 1.3 if is_hdr else line_h
                    if is_hdr:
                        total += line_h * 1.0
                    total += len(_wrap_w(ln.rstrip(), fn, fs, width)) * lhm
                return total

            hL = _estimate_h(sec["L"], col_w)
            hR = _estimate_h(sec["R"], col_w)
            needed = max(hL, hR)

            # 필요 높이가 남은 페이지보다 크고 y가 페이지 상단 근처가 아니면 새 페이지
            avail = y_top - margin
            if needed > avail and y_top < page_h - margin - 10:
                c.showPage()
                c.setFont(body_font, font_size)
                y_top = page_h - margin

            # 남은 공간에 맞게 line_h 스케일 (최소 0.75배까지 축소)
            lh_local = line_h
            avail = y_top - margin
            if needed > avail:
                scale = max(0.75, avail / needed)
                lh_local = line_h * scale

            y_L = _render_lines(sec["L"], margin, col_w, y_top, lh_local, allow_page_break=False)
            y_R = _render_lines(sec["R"], margin + col_w + COL_GAP, col_w, y_top, lh_local, allow_page_break=False)
            y = min(y_L, y_R) - line_h * 0.5

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


def _compress_resume_to_1page(
    text: str,
    photo_bytes: bytes | None = None,
    candidate_id: str = "",
) -> bytes:
    """이력서를 가능하면 1페이지로 압축. 단계적 line_h/margin/font 조정.

    커버레터와 별도로 처리 — 이력서는 내용이 많아 더 적극적으로 압축.
    """
    attempts = [
        {"line_h": 16.0, "margin_cm": 1.5, "font_size": 10},
        {"line_h": 15.0, "margin_cm": 1.3, "font_size": 10},
        {"line_h": 14.5, "margin_cm": 1.2, "font_size": 10},
        {"line_h": 14.0, "margin_cm": 1.2, "font_size": 10},
        {"line_h": 13.5, "margin_cm": 1.0, "font_size": 10},
        {"line_h": 13.0, "margin_cm": 1.0, "font_size": 9},
    ]
    best = None
    for kw in attempts:
        pdf_bytes = text_to_pdf_bytes(
            text,
            photo_bytes=photo_bytes,
            candidate_id=candidate_id,
            **kw,
        )
        try:
            with pikepdf.Pdf.open(io.BytesIO(pdf_bytes)) as p:
                pages = len(p.pages)
        except Exception:
            pages = 99
        if best is None:
            best = pdf_bytes
        if pages <= 1:
            return pdf_bytes
        best = pdf_bytes  # 가장 적은 페이지 옵션 저장
    return best  # 1페이지 불가능 시 최소 압축본 반환


# ── 2-column 섹션 마커 ────────────────────────────────────────────────────
# PII 엔진 regex를 통과하되 다른 텍스트와 충돌하지 않는 고유 마커
COL_START = "__BRIDGE_COL_START__"
COL_BREAK = "__BRIDGE_COL_BREAK__"
COL_END   = "__BRIDGE_COL_END__"


# ── PDF 에서 텍스트 추출 ───────────────────────────────────────────────────
def _extract_page_column_aware(page) -> str:
    """PyMuPDF block-based extraction — 2-column 자동 감지 + 마커 삽입.

    페이지를 세 zone 으로 분류:
      - FULL: 블록 폭이 페이지 폭의 55% 이상 (헤더·서머리)
      - L   : 중심 x < 페이지 중앙
      - R   : 중심 x > 페이지 중앙

    연속된 L+R 블록 구간은 2-column 영역으로 간주 → 마커 래핑.
    단일 컬럼 구간(L만 또는 R만)은 y 순서로 평범하게 emit.
    2-column 영역은 COL_START ... COL_BREAK ... COL_END 로 감싸서
    나중에 text_to_pdf_bytes 가 2-column 으로 렌더링할 수 있게 함.
    """
    blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
    text_blocks = [(b[0], b[1], b[2], b[3], b[4])
                   for b in blocks if b[6] == 0 and b[4].strip()]

    if not text_blocks:
        return page.get_text("text")

    page_w = page.rect.width
    mid    = page_w / 2

    def classify(b):
        x0, y0, x1, y1, _ = b
        w = x1 - x0
        if w > page_w * 0.55:
            return "FULL"
        cx = (x0 + x1) / 2
        return "L" if cx < mid else "R"

    # y 순서로 정렬 (안정 정렬)
    text_blocks.sort(key=lambda b: (b[1], b[0]))

    out: list[str] = []
    i = 0
    n = len(text_blocks)

    # 2-col 감지 임계값 — L/R 한 쌍 이상이 y 차이 ≤ Y_OVERLAP 이어야 "실제 2단"
    Y_OVERLAP = 30.0

    def _has_real_2col(L_items, R_items) -> bool:
        """L·R 에 y가 근접한 블록 쌍이 존재하면 True."""
        if not L_items or not R_items:
            return False
        for y_l, _ in L_items:
            for y_r, _ in R_items:
                if abs(y_l - y_r) <= Y_OVERLAP:
                    return True
        return False

    def _split_at_gap(items, full_items_y):
        """연속 블록에서 큰 세로 간격이 있으면 분할. full_items_y = 인접 FULL 블록의 y 경계."""
        return items  # 단순 구현 — 미사용

    while i < n:
        b = text_blocks[i]
        z = classify(b)

        if z == "FULL":
            out.append(b[4].strip())
            i += 1
            continue

        # 다음 FULL 블록까지 = 2-col 후보 구간
        j = i
        section_L: list[tuple[float, str]] = []
        section_R: list[tuple[float, str]] = []
        while j < n:
            nb = text_blocks[j]
            nz = classify(nb)
            if nz == "FULL":
                break
            if nz == "L":
                section_L.append((nb[1], nb[4].strip()))
            else:
                section_R.append((nb[1], nb[4].strip()))
            j += 1

        real_2col = _has_real_2col(section_L, section_R)

        if real_2col:
            # 각 L 은 가까운 R 이 있을 때만 core_L; 나머지는 header/footer 로 분리
            def _has_match(y, others):
                return any(abs(y - y2) <= Y_OVERLAP for y2, _ in others)

            core_L = [(y, t) for (y, t) in section_L if _has_match(y, section_R)]
            core_R = [(y, t) for (y, t) in section_R if _has_match(y, section_L)]
            outside = [(y, t) for (y, t) in (section_L + section_R)
                       if (y, t) not in core_L and (y, t) not in core_R]

            if not core_L or not core_R:
                # 쌍이 없으면 단일 컬럼으로
                for _, t in sorted(section_L + section_R, key=lambda x: x[0]):
                    out.append(t)
                i = j
                continue

            core_y_min = min(y for y, _ in core_L + core_R)
            core_y_max = max(y for y, _ in core_L + core_R)
            pre  = [(y, t) for (y, t) in outside if y < core_y_min]
            post = [(y, t) for (y, t) in outside if y > core_y_max]

            for _, t in sorted(pre, key=lambda x: x[0]):
                out.append(t)
            out.append(COL_START)
            out.extend(t for _, t in sorted(core_L, key=lambda x: x[0]))
            out.append(COL_BREAK)
            out.extend(t for _, t in sorted(core_R, key=lambda x: x[0]))
            out.append(COL_END)
            for _, t in sorted(post, key=lambda x: x[0]):
                out.append(t)
        else:
            # y-overlap 없음 → 단순 narrow 블록 나열 (section header 등). 단일 컬럼.
            merged = sorted(section_L + section_R, key=lambda x: x[0])
            out.extend(t for _, t in merged)

        i = j

    return "\n".join(out)


# ── 한국 도시명 (이력서 경력 섹션에서 위치 노출 방지) ────────────────────────
_KR_CITIES_STANDALONE = [
    "Seoul", "Busan", "Incheon", "Daegu", "Gwangju", "Daejeon", "Ulsan",
    "Suwon", "Seongnam", "Goyang", "Yongin", "Bucheon", "Ansan", "Anyang",
    "Cheonan", "Jeonju", "Cheongju", "Jeju", "Seosan", "Pohang", "Changwon",
    "Gumi", "Chuncheon", "Wonju", "Gangneung", "Mokpo", "Gwangmyeong",
    "Hwaseong", "Uijeongbu", "Dongducheon", "Paju", "Gimpo", "Gwangmyeong",
    "Gimhae", "Jinju", "Namyangju", "Asan", "Iksan", "Gunsan", "Pyeongtaek",
]


# ── 오펀 라벨 패턴 (내용 없는 라벨 라인 → 삭제) ──────────────────────────────
_ORPHAN_LINE_PATTERNS = [
    re.compile(r"^ü?\s*Your\s+current\s+location\s*:\s*$", re.IGNORECASE),
    re.compile(r"^ü?\s*Preferred\s+Location\s*:\s*$", re.IGNORECASE),
    re.compile(r"^ü?\s*Tel\s*&\s*(?:We\s+can\s+reach\s+you)?\s*:?\s*$", re.IGNORECASE),
    re.compile(r"^We\s+can\s+reach\s+you\s*:\s*$", re.IGNORECASE),
    re.compile(r"^\(?\+\s*\d{1,3}\)?\s*$"),                    # "(+82)" 단독
    re.compile(r"^ü?\s*Current\s+City\s*:\s*$", re.IGNORECASE),
    re.compile(r"^ü?\s*Address\s*:\s*$", re.IGNORECASE),
    re.compile(r"^ü?\s*Email\s*:\s*$", re.IGNORECASE),
    re.compile(r"^ü?\s*Phone\s*:\s*$", re.IGNORECASE),
]


def _is_orphan_line(text: str) -> bool:
    """블랭크/라벨만 남은 줄 감지 (연락처 아이콘·빈 라벨 등)."""
    t = text.strip()
    if not t or len(t) > 80:
        return False
    for pat in _ORPHAN_LINE_PATTERNS:
        if pat.match(t):
            return True
    return False


def _company_replacement(original: str) -> str:
    """회사명 → 일반화 치환."""
    low = original.lower()
    if "academy" in low:
        return "English Academy, Korea"
    if "school" in low and "language" not in low:
        return "English School, Korea"
    if "institute" in low or "language" in low or "hagwon" in low or "학원" in low:
        return "Language Institute, Korea"
    if "kindergarten" in low or "nursery" in low or "유치원" in low:
        return "Kindergarten, Korea"
    return "Language Institute, Korea"


def redact_pdf_preserve_layout(
    src_pdf_path: Path,
    pii_matches: list,
    candidate_name: str = "",
    min_len: int = 3,
) -> bytes:
    """
    원본 PDF 레이아웃 유지 + PII 제거 + 회사명 치환 + 오펀 라인 삭제.

    3-Pass 처리:
      Pass 1: 명시적 PII 문자열 redaction (+ 회사명 치환 텍스트 삽입)
      Pass 2: 이름 포함 문장 프리픽스 삭제 ("My name is {name}, and" 등)
      Pass 3: 오펀 라벨 라인 삭제 (내용 없는 연락처 라벨·잔존 국가코드)

    images=0, graphics=0 → 사진/벡터 배경 보존.

    Args:
        src_pdf_path: 원본 PDF 경로
        pii_matches: PIIMatch 객체 리스트 또는 (original, type) 튜플
                     type == 'company' → 일반화 치환 (Language Institute, Korea 등)
                     기타 → 공백 처리
        candidate_name: 이름 포함 문장 프리픽스 삭제용 (선택)

    Returns:
        redacted PDF bytes
    """
    import fitz

    # ── 입력 정규화: [(original, type), ...] ─────────────────────────────
    normalized: list[tuple[str, str]] = []
    for m in pii_matches or []:
        if hasattr(m, "original_value"):
            normalized.append((m.original_value, getattr(m, "type", "") or ""))
        elif isinstance(m, tuple) and len(m) >= 2:
            normalized.append((m[0], m[1]))
        elif isinstance(m, str):
            normalized.append((m, ""))

    # ── 치환 맵 구성: {검색문자열: 치환텍스트 or ""} ────────────────────
    redactions: dict[str, str] = {}
    for orig, ptype in normalized:
        if not orig or not isinstance(orig, str):
            continue
        key = orig.strip()
        if len(key) < min_len:
            continue
        if ptype == "company":
            redactions[key] = _company_replacement(key)
        else:
            redactions.setdefault(key, "")

    # ── 이름 포함 커버레터 프리픽스 (문장 복구용) ────────────────────────
    if candidate_name:
        nm = candidate_name.strip()
        # "My name is {name}, and" → 전체 삭제 (뒤의 "I am" 부터 시작)
        for variant in [nm, nm.upper(), nm.title()]:
            redactions[f"My name is {variant}, and"] = ""
            redactions[f"My name is {variant},"] = ""
            redactions[f"I am {variant},"] = ""

    # ── 한국 도시명 standalone 삭제 (업체명 redact 후 남은 도시 흔적) ─────
    # "Avalon Langcon Seosan" → "Avalon Langcon" 제거 후 "Seosan" 잔존 → 여기서 삭제
    for city in _KR_CITIES_STANDALONE:
        redactions.setdefault(city, "")

    # ── Substring 치환 키 제거 (긴 키에 포함된 짧은 회사명 키 skip) ────────
    # 예: "Avalon Langcon Seosan" + "Avalon Langcon" → 긴 것만 유지
    #     짧은 키 단독 치환으로 인한 중복 박스 방지
    _keys_desc = sorted(redactions.keys(), key=len, reverse=True)
    _filtered: dict[str, str] = {}
    for _k in _keys_desc:
        # 이미 들어온 긴 키의 substring이면 skip (단, 치환 텍스트가 동일한 경우에 한함)
        is_sub = False
        for _longer in _filtered.keys():
            if len(_k) >= len(_longer):
                continue
            if _k in _longer:
                # 동일 카테고리(company 치환 or 공백)일 때만 skip
                if _filtered[_longer] == redactions[_k]:
                    is_sub = True
                    break
                # 긴 쪽이 company 치환이고 짧은 쪽도 같은 회사 조각이면 skip
                if redactions[_k] and _filtered[_longer]:
                    is_sub = True
                    break
        if not is_sub:
            _filtered[_k] = redactions[_k]
    redactions = _filtered

    doc = fitz.open(str(src_pdf_path))
    total_hits = 0

    for page in doc:
        # ── Pass 1: PII + 회사명 치환 ──────────────────────────────────
        # 중복 방지를 위해 긴 키부터 처리 → 이미 덮인 영역 skip
        applied_rects: list = []  # 페이지 내 이미 redact된 rect 누적
        sorted_items = sorted(redactions.items(), key=lambda kv: -len(kv[0]))
        for text, repl in sorted_items:
            try:
                rects = page.search_for(text, quads=False)
            except Exception:
                continue
            for rect in rects:
                try:
                    # 기존 redact rect와 겹치면 skip (중복 치환 방지)
                    overlapped = False
                    for ex in applied_rects:
                        try:
                            if rect.intersects(ex):
                                overlapped = True
                                break
                        except Exception:
                            pass
                    if overlapped:
                        continue

                    if repl:
                        # 치환 텍스트 삽입 — 폰트 사이즈 상향 (최소 10, rect 높이 기준)
                        fs = max(10, int(rect.height * 0.9))
                        page.add_redact_annot(
                            rect,
                            text=repl,
                            fontsize=fs,
                            fill=(1, 1, 1),
                            text_color=(0, 0, 0),
                            align=0,
                        )
                    else:
                        # 단순 제거 (fill=None → 원래 배경 유지)
                        page.add_redact_annot(rect, fill=None)
                    applied_rects.append(rect)
                    total_hits += 1
                except Exception:
                    pass

        try:
            page.apply_redactions(images=0, graphics=0)
        except TypeError:
            try:
                page.apply_redactions()
            except Exception as e:
                log.warning(f"apply_redactions Pass1 실패 p{page.number}: {e}")
        except Exception as e:
            log.warning(f"apply_redactions Pass1 실패 p{page.number}: {e}")

        # ── Pass 2: 오펀 라벨 라인 삭제 ────────────────────────────────
        try:
            td = page.get_text("dict")
        except Exception:
            td = {"blocks": []}

        orphan_rects: list = []
        for block in td.get("blocks", []):
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                line_text = "".join(s.get("text", "") for s in spans)
                if _is_orphan_line(line_text):
                    bb = line.get("bbox")
                    if bb:
                        # 라인 bbox에 약간 여유 (좌우 아이콘까지 포함)
                        r = fitz.Rect(bb)
                        r.x0 = max(0, r.x0 - 20)  # 아이콘 영역까지 확장
                        r.x1 = r.x1 + 10
                        orphan_rects.append(r)

        for rect in orphan_rects:
            try:
                page.add_redact_annot(rect, fill=None)
                total_hits += 1
            except Exception:
                pass

        if orphan_rects:
            try:
                page.apply_redactions(images=0, graphics=0)
            except TypeError:
                try:
                    page.apply_redactions()
                except Exception:
                    pass
            except Exception:
                pass

        # ── Pass 2.5: CONTACT/연락처 섹션 전체 덮기 (템플릿 사이드바) ──────
        # 꾸며진 사이드바에 있는 "CONTACT ME", "CONTACT", "연락처" 등 헤딩 감지
        # → 그 아래부터 다음 헤딩 전까지 사이드바 배경색으로 덮기
        try:
            _CONTACT_HEADING = re.compile(
                r"^\s*(contact(\s*(me|info|us|details))?|get\s*in\s*touch|"
                r"personal(\s*(info|details))?|details|info|\uc5f0\ub77d\ucc98)\s*$",
                re.IGNORECASE,
            )
            page_h = page.rect.height
            page_w = page.rect.width
            td25 = page.get_text("dict")

            contact_region = None
            for block in td25.get("blocks", []):
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    text = "".join(s.get("text", "") for s in spans).strip()
                    if not text or not _CONTACT_HEADING.match(text):
                        continue
                    bb = line.get("bbox")
                    if not bb:
                        continue
                    # 사이드바 여부: 좌측 35% 또는 우측 65% 이후
                    left_side  = bb[2] <= page_w * 0.38
                    right_side = bb[0] >= page_w * 0.62
                    if not (left_side or right_side):
                        continue
                    if left_side:
                        contact_region = {
                            "y_start": bb[1] - 3,
                            "x_min": 0,
                            "x_max": page_w * 0.38,
                        }
                    else:
                        contact_region = {
                            "y_start": bb[1] - 3,
                            "x_min": page_w * 0.62,
                            "x_max": page_w,
                        }
                    break
                if contact_region:
                    break

            if contact_region:
                # 다음 헤딩 탐색 (같은 x 범위 내)
                y_end = None
                for block in td25.get("blocks", []):
                    for line in block.get("lines", []):
                        bb = line.get("bbox")
                        if not bb or bb[1] <= contact_region["y_start"] + 5:
                            continue
                        if bb[0] < contact_region["x_min"] - 2 or bb[2] > contact_region["x_max"] + 2:
                            continue
                        spans = line.get("spans", [])
                        text = "".join(s.get("text", "") for s in spans).strip()
                        if len(text) < 3 or len(text) > 30:
                            continue
                        is_bold = any(int(s.get("flags", 0)) & 16 for s in spans)
                        is_upper = text.isupper() or (text.replace(" ", "").isalpha() and text == text.upper())
                        if is_bold or is_upper:
                            y_end = bb[1] - 2
                            break
                    if y_end:
                        break
                if y_end is None:
                    y_end = min(contact_region["y_start"] + 220, page_h)

                # 덮기 y_start 확장: 사이드바 상단 사진 바로 아래부터 덮기
                # (헤딩 위의 장식 선/빈 박스까지 포함)
                try:
                    sidebar_photo_y1 = None
                    for img in page.get_images(full=True):
                        xref = img[0]
                        try:
                            rects_img = page.get_image_rects(xref)
                        except Exception:
                            continue
                        for r in rects_img:
                            # 사이드바 x 범위 내 + 상단 1/3 영역의 이미지만
                            if r.x0 < contact_region["x_min"] - 2 or r.x1 > contact_region["x_max"] + 2:
                                continue
                            if r.y0 > page_h * 0.35:
                                continue
                            if r.y1 < contact_region["y_start"]:
                                if sidebar_photo_y1 is None or r.y1 > sidebar_photo_y1:
                                    sidebar_photo_y1 = r.y1
                    if sidebar_photo_y1 is not None and sidebar_photo_y1 < contact_region["y_start"]:
                        # 사진 하단 2px 아래부터 덮기
                        contact_region["y_start"] = sidebar_photo_y1 + 2
                except Exception:
                    pass

                # 배경색 샘플링 (헤딩 라인 중간부 — 장식선 회피)
                try:
                    heading_center_y = (contact_region["y_start"] + y_end) / 2
                    sample_clip = fitz.Rect(
                        contact_region["x_min"] + 5,
                        max(0, heading_center_y - 2),
                        contact_region["x_min"] + 15,
                        heading_center_y + 2,
                    )
                    sp = page.get_pixmap(clip=sample_clip)
                    if sp.n >= 3 and sp.samples:
                        idx = (sp.h // 2) * sp.stride + (sp.w // 2) * sp.n
                        bg25 = (
                            sp.samples[idx] / 255.0,
                            sp.samples[idx + 1] / 255.0,
                            sp.samples[idx + 2] / 255.0,
                        )
                    else:
                        bg25 = (1, 1, 1)
                except Exception:
                    bg25 = (1, 1, 1)

                cover = fitz.Rect(
                    contact_region["x_min"],
                    contact_region["y_start"],
                    contact_region["x_max"],
                    y_end,
                )
                try:
                    page.draw_rect(cover, color=bg25, fill=bg25, width=0)
                    total_hits += 1
                except Exception:
                    pass
        except Exception as e:
            log.warning(f"CONTACT 섹션 삭제 Pass2.5 실패 p{page.number}: {e}")

        # ── Pass 2.6: Dangling preposition 정리 ──────────────────────────
        # PyMuPDF apply_redactions는 redact 경계에서 라인을 분리함.
        # 같은 y-좌표에 여러 라인 프래그먼트가 있으면 원래 한 문장이었다는 의미.
        # 첫 프래그먼트가 전치사로 끝나면 → 해당 전치사 redact (공백 제거)
        try:
            _DANGLE_WORDS = {
                "in", "at", "on", "from", "to", "of", "with", "by", "for",
                "and", "or", "as", "the", "a", "an", "into", "onto", "upon",
                "into", "over", "under", "near",
            }
            td26 = page.get_text("dict")
            # get_text("words") → 각 단어의 정확한 bbox
            word_tuples = page.get_text("words")
            # [(x0,y0,x1,y1,word,block_no,line_no,word_no), ...]

            # y-band bucket (같은 시각적 라인)
            lines_by_y: dict = {}
            for block in td26.get("blocks", []):
                for line in block.get("lines", []):
                    bb = line.get("bbox")
                    spans = line.get("spans", [])
                    if not bb or not spans:
                        continue
                    y_key = round(bb[1] / 2) * 2
                    lines_by_y.setdefault(y_key, []).append((bb, line))

            dangle_redacts: list = []
            for y_key, items in lines_by_y.items():
                if len(items) < 2:
                    continue
                items.sort(key=lambda t: t[0][0])
                for i in range(len(items) - 1):
                    bb_a, line_a = items[i]
                    bb_b, _ = items[i + 1]
                    gap = bb_b[0] - bb_a[2]
                    if gap < 15:
                        continue
                    spans_a = line_a.get("spans", [])
                    text_a = "".join(s.get("text", "") for s in spans_a).rstrip()
                    if not text_a:
                        continue
                    words = text_a.split()
                    if not words:
                        continue
                    last_w = words[-1].strip(",.;:!?()\"'").lower()
                    if last_w not in _DANGLE_WORDS:
                        continue
                    # get_text("words") 에서 bb_a 내부의 마지막 단어 bbox 찾기
                    cand = None
                    for wt in word_tuples:
                        wx0, wy0, wx1, wy1, wtext = wt[0], wt[1], wt[2], wt[3], wt[4]
                        # 같은 라인 범위 (y 중간값이 bb_a 내부)
                        wy_mid = (wy0 + wy1) / 2
                        if not (bb_a[1] - 1 <= wy_mid <= bb_a[3] + 1):
                            continue
                        if wx0 < bb_a[0] - 1 or wx1 > bb_a[2] + 1:
                            continue
                        # 단어 match (전치사)
                        if wtext.strip(",.;:!?()\"'").lower() != last_w:
                            continue
                        # 가장 오른쪽(끝) 후보
                        if cand is None or wx1 > cand[2]:
                            cand = (wx0, wy0, wx1, wy1)
                    if cand is None:
                        continue
                    cut_rect = fitz.Rect(
                        cand[0] - 1, cand[1] - 1,
                        cand[2] + 2, cand[3] + 1,
                    )
                    dangle_redacts.append(cut_rect)

            for rect in dangle_redacts:
                try:
                    page.add_redact_annot(rect, fill=None)
                    total_hits += 1
                except Exception:
                    pass
            if dangle_redacts:
                try:
                    page.apply_redactions(images=0, graphics=0)
                except TypeError:
                    try:
                        page.apply_redactions()
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception as e:
            log.warning(f"Dangling preposition Pass2.6 실패 p{page.number}: {e}")

        # ── Pass 3: 연락처 아이콘 덮기 (소형 벡터 드로잉) ─────────────────
        # Canva 템플릿의 좌측 사이드바 phone/email/location 아이콘 등
        # graphics redaction은 불안정 → 사이드바 배경색으로 직접 페인트
        try:
            page_h = page.rect.height
            page_w = page.rect.width
            drawings = page.get_drawings()
            icon_rects: list = []
            for d in drawings:
                try:
                    rr = d.get("rect")
                    if rr is None:
                        continue
                    r = fitz.Rect(rr)
                    w, h = r.width, r.height
                    if not (3 <= w <= 28 and 3 <= h <= 28):
                        continue
                    if max(w, h) / max(min(w, h), 0.1) > 3.5:
                        continue
                    in_left = r.x1 <= page_w * 0.28
                    in_top  = r.y1 <= page_h * 0.55
                    if in_left and in_top:
                        icon_rects.append(r)
                except Exception:
                    continue

            if icon_rects:
                # 사이드바 배경색 샘플링 (아이콘 사이 빈 공간)
                bg_color = None
                try:
                    # 아이콘들의 평균 y 위치 근처에서 왼쪽 끝 사이드바 색상 샘플
                    avg_y = sum((r.y0 + r.y1) / 2 for r in icon_rects) / len(icon_rects)
                    # 페이지 좌측 끝 (x=5) 근처에서 샘플 (아이콘 바깥)
                    sample_rect = fitz.Rect(2, max(0, avg_y - 2), 8, min(page_h, avg_y + 2))
                    pix = page.get_pixmap(clip=sample_rect)
                    if pix.n >= 3 and pix.samples:
                        # 중앙 픽셀 RGB
                        idx = (pix.h // 2) * pix.stride + (pix.w // 2) * pix.n
                        r_c = pix.samples[idx] / 255.0
                        g_c = pix.samples[idx + 1] / 255.0
                        b_c = pix.samples[idx + 2] / 255.0
                        bg_color = (r_c, g_c, b_c)
                except Exception:
                    bg_color = None

                # 배경색 위에 덮어쓰기 (draw_rect with fill)
                for rect in icon_rects:
                    try:
                        # 아이콘보다 약간 크게 덮기 (1px 여유)
                        cover = fitz.Rect(
                            max(0, rect.x0 - 1),
                            max(0, rect.y0 - 1),
                            rect.x1 + 1,
                            rect.y1 + 1,
                        )
                        if bg_color:
                            page.draw_rect(cover, color=bg_color, fill=bg_color, width=0)
                        else:
                            # 배경색 미검출 → 흰색 폴백
                            page.draw_rect(cover, color=(1, 1, 1), fill=(1, 1, 1), width=0)
                        total_hits += 1
                    except Exception:
                        pass
        except Exception as e:
            log.warning(f"icon removal Pass3 실패 p{page.number}: {e}")

    try:
        doc.set_metadata({
            "author": "", "title": "", "subject": "",
            "keywords": "", "creator": "", "producer": "",
        })
    except Exception:
        pass

    out_bytes = doc.tobytes(deflate=True, garbage=4, clean=True)
    total_pages = len(doc)
    doc.close()
    log.info(f"redact v3.4: {total_hits}건 처리 / {total_pages}페이지 / {len(out_bytes)//1024}KB")
    return out_bytes


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


# ── 전체 페이지 자동 줄간격 계산 ────────────────────────────────────────────
def _auto_line_h(
    text: str,
    font_size: int = 10,
    margin_cm: float = 1.5,
    has_photo: bool = True,
) -> float:
    """텍스트가 사용하는 모든 페이지를 ~90% 채우도록 line_h 자동 계산.
    마지막 페이지의 빈 여백이 절반 이상 남지 않도록 전 페이지 합산으로 분배.
    반환 범위: 16 ~ 30 pt.
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

    # 2-column 섹션 분리 (L+R을 max(L,R)으로 계산 — 이중계산 방지)
    _COL_START = COL_START
    _COL_BREAK = COL_BREAK
    _COL_END   = COL_END

    def _count_units(ls: list[str], col_w_ratio: float = 1.0) -> float:
        """lines → 세로 유닛 합산. col_w_ratio < 1이면 2-col 폭으로 줄바꿈."""
        units = 0.0
        effective_w = max_w * col_w_ratio
        for raw_line in ls:
            stripped = raw_line.strip()
            if stripped in (_COL_START, _COL_BREAK, _COL_END):
                continue
            if stripped == "":
                units += 0.35
                continue
            is_hdr = bool(_HDR_RE2.match(stripped))
            fn = bold_font if is_hdr else body_font
            fs = font_size + 1 if is_hdr else font_size
            lh_mult = 1.2 if is_hdr else 1.0
            if is_hdr:
                units += 0.2
            # 2-col 폭으로 실제 줄 수 계산
            if _sw2(raw_line.rstrip(), fn, fs) <= effective_w:
                wrapped_cnt = 1
            else:
                wrapped_cnt = len(_wrap2(raw_line.rstrip(), fn, fs))
            units += wrapped_cnt * lh_mult
        return units

    # 2-column 구간 분리하여 max(L_units, R_units) 사용
    COL_W_RATIO = 0.47   # 2-col 한 컬럼 폭 ≒ 전체의 47%
    total_units = 0.0
    in_col = False
    L_lines: list[str] = []
    R_lines: list[str] = []
    cur_bucket = None
    full_lines: list[str] = []

    for ln in lines:
        st = ln.strip()
        if st == _COL_START:
            if full_lines:
                total_units += _count_units(full_lines)
                full_lines = []
            in_col = True
            cur_bucket = L_lines
        elif st == _COL_BREAK and in_col:
            cur_bucket = R_lines
        elif st == _COL_END and in_col:
            lu = _count_units(L_lines, COL_W_RATIO)
            ru = _count_units(R_lines, COL_W_RATIO)
            total_units += max(lu, ru)
            L_lines, R_lines = [], []
            in_col = False
            cur_bucket = None
        elif in_col:
            cur_bucket.append(ln)
        else:
            full_lines.append(ln)

    if full_lines:
        total_units += _count_units(full_lines)
    if in_col:  # 닫힘 없는 2-col
        lu = _count_units(L_lines, COL_W_RATIO)
        ru = _count_units(R_lines, COL_W_RATIO)
        total_units += max(lu, ru)

    if total_units <= 0:
        return 18.0

    # 팽창 보정 (A구역 압축 반영, 1.1)
    total_units *= 1.1

    # 일반 페이지(사진 없음) 사용 가능 높이
    page_avail_h = page_h - margin * 2

    # 1) 최소 line_h 기준으로 필요한 페이지 수 계산
    MIN_LH = 16.0
    first_page_units = avail_h / MIN_LH       # 첫 페이지가 담을 수 있는 유닛 (최소 간격 기준)
    rest_units       = max(0.0, total_units - first_page_units)
    rest_pages       = max(0, int((rest_units * MIN_LH) / page_avail_h) + (1 if rest_units > 0 else 0))
    pages_needed     = 1 + rest_pages

    # 2) 전체 페이지 합산 사용 가능 높이
    total_avail_h = avail_h + (pages_needed - 1) * page_avail_h

    # 3) 마지막 페이지가 비지 않도록 line_h 를 최대화
    #    3페이지가 필요한 내용이면 line_h 를 3페이지 한계까지 늘려 마지막 페이지도 ~80% 채움.
    #    공식: line_h = total_avail / total_units  (해당 페이지 수에서 최대치)
    def _max_lh_for_pages(pages: int) -> float:
        avail = avail_h + (pages - 1) * page_avail_h
        return avail / total_units          # 이 line_h 이하에서는 pages 에 반드시 들어감

    # N페이지에 딱 맞는 최대 line_h (경계값) 의 95%를 사용 → 안전 여유
    best_lh = _max_lh_for_pages(pages_needed) * 0.95
    return max(16.0, min(26.0, best_lh))


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
    # v3.0 (2026-04-23): 레이아웃 보존 모드 — 원본 PDF + PII 서지컬 제거
    cover_pdf_path:  Path | None = None,
    resume_pdf_path: Path | None = None,
    cover_pii_strings:  list | None = None,  # PIIMatch 객체 또는 (str, type) 또는 str
    resume_pii_strings: list | None = None,
    # v3.1 (2026-04-23): 회사명 치환 + 오펀 라벨 삭제 + 이름 프리픽스 삭제
    candidate_name: str = "",
) -> tuple[Path, int]:
    """
    PDF 조립 + 압축.

    v3.0 우선 경로: cover_pdf_path / resume_pdf_path 제공 시 원본 레이아웃 유지
                   (PyMuPDF 서지컬 redaction — Canva 템플릿 색상·사진·배치 보존)
    fallback 경로: pdf_path 없으면 cleaned_text로 재조립 (레이아웃 파괴)

    Returns:
        (output_path, file_size_bytes)
    """
    page_w, page_h = A4
    pdf_parts: list[bytes] = []

    # ── 레이아웃 v3.0: 원본 PDF 우선 사용 (Canva 템플릿 보존) ─────────────────
    #   cover/resume PDF 경로 제공 시 → redact_pdf_preserve_layout (layout 유지)
    #   경로 없을 때만 → 기존 text→PDF 재조립 (fallback)
    _first_added = False

    if cover_pdf_path and Path(cover_pdf_path).exists():
        try:
            pdf_parts.append(redact_pdf_preserve_layout(
                Path(cover_pdf_path),
                cover_pii_strings or [],
                candidate_name=candidate_name,
            ))
            _first_added = True
        except Exception as e:
            log.warning(f"커버 redact 실패 → text fallback: {e}")
            if cover_text and cover_text.strip():
                _cover_lh = _auto_line_h(cover_text, font_size=10, margin_cm=1.5, has_photo=False)
                pdf_parts.append(text_to_pdf_bytes(
                    cover_text, photo_bytes=None, candidate_id="",
                    line_h=_cover_lh, margin_cm=1.5, font_size=10,
                ))
                _first_added = True
    elif cover_text and cover_text.strip():
        _cover_lh = _auto_line_h(cover_text, font_size=10, margin_cm=1.5, has_photo=False)
        pdf_parts.append(text_to_pdf_bytes(
            cover_text,
            photo_bytes=None,
            candidate_id="",
            line_h=_cover_lh,
            margin_cm=1.5,
            font_size=10,
        ))
        _first_added = True

    if resume_pdf_path and Path(resume_pdf_path).exists():
        try:
            pdf_parts.append(redact_pdf_preserve_layout(
                Path(resume_pdf_path),
                resume_pii_strings or [],
                candidate_name=candidate_name,
            ))
            _first_added = True
        except Exception as e:
            log.warning(f"이력서 redact 실패 → text fallback: {e}")
            if resume_text and resume_text.strip():
                pdf_parts.append(_compress_resume_to_1page(
                    resume_text,
                    photo_bytes=photo_bytes,
                    candidate_id=str(candidate_id),
                ))
                _first_added = True
    elif resume_text and resume_text.strip():
        pdf_parts.append(_compress_resume_to_1page(
            resume_text,
            photo_bytes=photo_bytes,
            candidate_id=str(candidate_id),
        ))
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
