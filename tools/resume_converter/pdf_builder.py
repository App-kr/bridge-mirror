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
import pdfplumber

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
    return f"{candidate_id}_{nat}_{gen}({yr}born).pdf"


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
def text_to_pdf_bytes(text: str, title: str = "") -> bytes:
    """plain text → PDF bytes (reportlab)."""
    buf = io.BytesIO()
    page_w, page_h = A4
    c   = rl_canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica", 10)

    if title:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1.5 * cm, page_h - 1.5 * cm, title)
        c.setFont("Helvetica", 10)
        y = page_h - 2.5 * cm
    else:
        y = page_h - 1.5 * cm

    line_h  = 14
    max_w   = page_w - 3 * cm
    margin  = 1.5 * cm

    # 간단한 줄 바꿈 (CJK 미처리 — 추후 확장 가능)
    for line in text.split("\n"):
        # 긴 줄 자동 줄바꿈
        while len(line) * 6 > max_w:
            chunk = line[:int(max_w / 6)]
            c.drawString(margin, y, chunk)
            y -= line_h
            line = line[int(max_w / 6):]
            if y < 2 * cm:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = page_h - 1.5 * cm

        c.drawString(margin, y, line)
        y -= line_h
        if y < 2 * cm:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = page_h - 1.5 * cm

    c.save()
    return buf.getvalue()


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
        pdf_parts.append(text_to_pdf_bytes(cover_text, "Cover Letter"))

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
