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
    "usa": "미국", "us": "미국", "canada": "캐나다", "uk": "영국",
    "australia": "호주", "new zealand": "뉴질랜드", "south africa": "남아공",
    "ireland": "아일랜드", "philippines": "필리핀",
}

def build_filename(
    candidate_id: str,
    nationality: str = "",
    gender: str = "",
    birth_year: str = "",
) -> str:
    """
    예: 3126_미국_여성(99born).pdf
    """
    nat = _NAT_MAP.get(nationality.lower(), nationality) or "미상"
    gen = _GENDER_MAP.get(gender.lower(), gender) or "미상"
    yr  = str(birth_year)[-2:] if birth_year else "00"
    return f"{candidate_id}{nat}_{gen}({yr}born).pdf"


# ── 1페이지: 커버 생성 ─────────────────────────────────────────────────────
def _build_cover_page(
    packet:       io.BytesIO,
    candidate_id: str,
    photo_bytes:  bytes | None,
    page_w:       float,
    page_h:       float,
) -> None:
    """reportlab으로 커버 페이지 생성."""
    c = rl_canvas.Canvas(packet, pagesize=(page_w, page_h))

    # 강사 ID (좌상단)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1.5 * cm, page_h - 2 * cm, f"ID: {candidate_id}")

    c.setFont("Helvetica", 10)
    c.drawString(1.5 * cm, page_h - 3 * cm, "BRIDGE ESL Teacher Application")
    c.line(1.5 * cm, page_h - 3.3 * cm, page_w - 1.5 * cm, page_h - 3.3 * cm)

    # 증명사진 (우상단)
    if photo_bytes:
        try:
            img = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
            img = img.resize((150, 200), Image.LANCZOS)

            tmp_img = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            img.save(tmp_img.name, format="JPEG", quality=85, dpi=(150, 150))
            tmp_img.close()

            img_x = page_w - 1.5 * cm - 5 * cm
            img_y = page_h - 2 * cm - 7 * cm
            c.drawImage(tmp_img.name, img_x, img_y, width=5 * cm, height=7 * cm,
                        preserveAspectRatio=True, mask="auto")

            import os; os.unlink(tmp_img.name)
        except Exception as e:
            log.warning(f"사진 삽입 실패: {e}")

    c.showPage()
    c.save()


# ── 텍스트 → PDF 변환 ──────────────────────────────────────────────────────
def text_to_pdf_bytes(text: str, title: str = "",
                      line_h: float = 16, margin_cm: float = 1.5,
                      font_size: int = 10) -> bytes:
    """plain text → PDF bytes (reportlab, 한글 지원).

    맑은 고딕 TTF가 있으면 한글 렌더링, 없으면 Helvetica 폴백.
    CJK 글자는 폭을 12px로 계산해 줄바꿈 정확도 향상.
    """
    buf     = io.BytesIO()
    page_w, page_h = A4
    c       = rl_canvas.Canvas(buf, pagesize=A4)
    margin  = margin_cm * cm
    max_w   = page_w - margin * 2

    # 폰트 선택
    body_font  = _KOREAN_FONT      if _KOREAN_FONT      else "Helvetica"
    title_font = _KOREAN_FONT_BOLD if _KOREAN_FONT_BOLD else "Helvetica-Bold"

    def _line_width(s: str) -> float:
        """글자폭 추정: CJK 12px, ASCII 6px."""
        return sum(12 if ord(ch) > 0x2E7F else 6 for ch in s)

    def _draw_line(canvas_obj, s: str, x: float, y: float) -> None:
        canvas_obj.drawString(x, y, s)

    def _new_page() -> float:
        c.showPage()
        c.setFont(body_font, font_size)
        return page_h - margin

    c.setFont(body_font, font_size)

    title_size = font_size + 2
    if title:
        c.setFont(title_font, title_size)
        c.drawString(margin, page_h - margin, title)
        c.setFont(body_font, font_size)
        y = page_h - margin - line_h * 1.5
    else:
        y = page_h - margin

    for raw_line in text.split("\n"):
        # 긴 줄 자동 줄바꿈 (CJK 폭 보정)
        while _line_width(raw_line) > max_w:
            # 들어갈 수 있는 글자 수 계산
            acc = 0
            cut = 0
            for ch in raw_line:
                w = 12 if ord(ch) > 0x2E7F else 6
                if acc + w > max_w:
                    break
                acc += w
                cut += 1
            chunk    = raw_line[:cut]
            raw_line = raw_line[cut:]
            _draw_line(c, chunk, margin, y)
            y -= line_h
            if y < margin:
                y = _new_page()

        _draw_line(c, raw_line, margin, y)
        y -= line_h
        if y < margin:
            y = _new_page()

    c.save()
    return buf.getvalue()


# ── 커버레터 1페이지 압축 ───────────────────────────────────────────────────
def _compress_cover_to_1page(text: str) -> bytes:
    """커버레터가 1페이지 초과 시 단계적 압축. 최대 1페이지."""
    attempts = [
        {"line_h": 16,   "margin_cm": 1.5, "font_size": 11},
        {"line_h": 14,   "margin_cm": 1.5, "font_size": 11},
        {"line_h": 14,   "margin_cm": 1.2, "font_size": 11},
        {"line_h": 13.6, "margin_cm": 1.0, "font_size": 10},
    ]
    for kw in attempts:
        pdf_bytes = text_to_pdf_bytes(text, "Cover Letter", **kw)
        try:
            with pikepdf.Pdf.open(io.BytesIO(pdf_bytes)) as p:
                if len(p.pages) <= 1:
                    return pdf_bytes
        except Exception:
            return pdf_bytes
    return pdf_bytes  # 최소 설정으로 그냥 반환


# ── PDF 에서 텍스트 추출 ───────────────────────────────────────────────────
def extract_text_from_pdf(pdf_path: Path) -> str:
    """pdfplumber로 텍스트 추출."""
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

    # ── 1페이지: 커버 ────────────────────────────────────────────────────
    cover_buf = io.BytesIO()
    _build_cover_page(cover_buf, candidate_id, photo_bytes, page_w, page_h)
    pdf_parts.append(cover_buf.getvalue())

    # ── 텍스트 섹션 ──────────────────────────────────────────────────────
    if cover_text and cover_text.strip():
        pdf_parts.append(_compress_cover_to_1page(cover_text))

    if resume_text and resume_text.strip():
        pdf_parts.append(text_to_pdf_bytes(resume_text, "Curriculum Vitae"))

    if rec_text and rec_text.strip():
        pdf_parts.append(text_to_pdf_bytes(rec_text, "Recommendation Letter"))

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
