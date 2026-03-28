"""
pipeline.py — BRIDGE Resume Converter
오케스트레이터 (완전자동 / 반자동 모드)

PAUSE 포인트 (반자동):
  1: 파일 분류 확인
  2: 얼굴 크롭 결과 확인
  3: PII 탐지 결과 + 집중점검
  4: PDF 미리보기 최종 확인
  5: 파일명 확인 후 저장
"""

from __future__ import annotations

import io
import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Optional

from .file_classifier import detect_file_type, INBOX_DIR
from .face_crop        import crop_face, crop_face_from_bytes, FaceNotFoundError
from .pii_engine       import analyze_pii, PIIResult, load_api_key
from .pdf_builder      import build_pdf, build_filename, extract_text_from_pdf
from .security         import encrypt_file, secure_delete, secure_delete_dir, log_processing
from .sheets_connector import get_candidate_info, write_processed_entry

log = logging.getLogger("pipeline")

BASE_DIR       = Path(__file__).parent
PROCESSING_DIR = BASE_DIR / "processing"
OUTPUT_DIR     = BASE_DIR / "output"
ORIGINALS_DIR  = BASE_DIR / "originals"


# ── 파이프라인 상태 ────────────────────────────────────────────────────────
class PausePoint(Enum):
    CLASSIFY = auto()
    FACE_CROP = auto()
    PII_CHECK = auto()
    PDF_PREVIEW = auto()
    SAVE = auto()

@dataclass
class PipelineJob:
    candidate_id: str
    files:        dict[str, Path] = field(default_factory=dict)
    # 타입별 파일: {"photo": Path, "resume": Path, "cover": Path, "rec": Path}

    # 처리 결과
    photo_bytes:  Optional[bytes]    = None
    cover_pii:    Optional[PIIResult] = None
    resume_pii:   Optional[PIIResult] = None
    rec_pii:      Optional[PIIResult] = None
    output_path:  Optional[Path]     = None
    output_size:  int = 0

    # 메타 (구글시트에서 조회)
    nationality:  str = ""
    gender:       str = ""
    birth_year:   str = ""

    # 오류
    errors:       list[str] = field(default_factory=list)
    warnings:     list[str] = field(default_factory=list)


# ── 콜백 타입 ─────────────────────────────────────────────────────────────
# pause_callback(point, job) → bool (True=계속, False=취소)
PauseCallback = Callable[[PausePoint, PipelineJob], bool]


class Pipeline:
    """이력서 변환 파이프라인."""

    def __init__(
        self,
        auto_mode:      bool = True,
        pause_callback: PauseCallback | None = None,
        on_progress:    Callable[[str], None] | None = None,
    ):
        self.auto_mode      = auto_mode
        self.pause_callback = pause_callback
        self.on_progress    = on_progress or (lambda msg: log.info(msg))
        self.api_key        = load_api_key()

    def _emit(self, msg: str):
        self.on_progress(msg)

    def _pause(self, point: PausePoint, job: PipelineJob) -> bool:
        """반자동 모드에서 pause 처리. True=계속, False=취소."""
        if self.auto_mode or self.pause_callback is None:
            return True
        return self.pause_callback(point, job)

    # ── 1단계: 파일 분류 확인 ─────────────────────────────────────────────
    def _step_classify(self, job: PipelineJob, folder: Path) -> bool:
        self._emit(f"[1/5] 파일 분류 확인: {folder.name}")
        for f in folder.iterdir():
            ftype = detect_file_type(f)
            if ftype != "unknown":
                job.files[ftype] = f
            else:
                job.warnings.append(f"미분류 파일: {f.name}")

        if not job.files:
            job.errors.append("분류된 파일 없음")
            return False

        self._emit(f"  분류됨: {list(job.files.keys())}")
        return self._pause(PausePoint.CLASSIFY, job)

    # ── 2단계: 얼굴 크롭 ─────────────────────────────────────────────────
    def _step_face_crop(self, job: PipelineJob) -> bool:
        self._emit("[2/5] 얼굴 크롭")
        photo_path = job.files.get("photo")
        if not photo_path:
            # 별도 사진 없음 → 이력서 PDF 내장 이미지 탐색
            resume_path = job.files.get("resume")
            if resume_path and resume_path.suffix.lower() == ".pdf":
                self._emit("  별도 사진 없음 — 이력서 내 사진 탐색 중...")
                extracted = _extract_photo_from_pdf(resume_path)
                if extracted:
                    job.photo_bytes = extracted
                    self._emit(f"  이력서 내장 사진 사용 ({len(extracted)//1024}KB)")
                    return self._pause(PausePoint.FACE_CROP, job)
                else:
                    self._emit("  내장 사진 없음 — 건너뜀")
            else:
                self._emit("  사진 없음 — 건너뜀")
            return self._pause(PausePoint.FACE_CROP, job)

        try:
            tmp_dir = PROCESSING_DIR / job.candidate_id
            tmp_dir.mkdir(parents=True, exist_ok=True)
            out     = tmp_dir / "photo_crop.jpg"
            job.photo_bytes = crop_face(photo_path, out)
            # 임시파일 암호화
            encrypt_file(out, out.with_suffix(".enc"))
            secure_delete(out)
            self._emit(f"  크롭 완료 ({len(job.photo_bytes)//1024}KB)")
        except FaceNotFoundError as e:
            job.warnings.append(f"얼굴 미감지: {e}")
            self._emit(f"  [경고] {e} — 수동 크롭 필요")
        except Exception as e:
            job.errors.append(f"크롭 오류: {e}")
            return False

        return self._pause(PausePoint.FACE_CROP, job)

    # ── 3단계: PII 제거 ──────────────────────────────────────────────────
    def _step_pii(self, job: PipelineJob) -> bool:
        self._emit("[3/5] PII 탐지 + 제거")

        def _process(ftype: str, label: str) -> Optional[PIIResult]:
            p = job.files.get(ftype)
            if not p:
                return None
            text = _extract_text(p)
            if not text.strip():
                return None
            result = analyze_pii(text, self.api_key)
            self._emit(f"  {label}: {len(result.pii_found)}개 제거, "
                       f"{len(result.uncertain)}개 불확실")
            return result

        job.cover_pii  = _process("cover",  "커버레터")
        job.resume_pii = _process("resume", "이력서")
        job.rec_pii    = _process("rec",    "추천서")

        return self._pause(PausePoint.PII_CHECK, job)

    # ── 4단계: PDF 생성 ──────────────────────────────────────────────────
    def _step_build_pdf(self, job: PipelineJob) -> bool:
        self._emit("[4/5] PDF 조립")

        # 구글시트에서 메타 조회
        try:
            info = get_candidate_info(job.candidate_id)
            if info:
                job.nationality = info.get("nationality", "")
                job.gender      = info.get("gender", "")
                job.birth_year  = info.get("birth_year", "")
                self._emit(f"  시트 조회: {job.nationality}/{job.gender}/{job.birth_year}")
        except Exception as e:
            job.warnings.append(f"시트 조회 실패: {e}")

        out_path, size = build_pdf(
            candidate_id = job.candidate_id,
            nationality  = job.nationality,
            gender       = job.gender,
            birth_year   = job.birth_year,
            photo_bytes  = job.photo_bytes,
            cover_text   = job.cover_pii.cleaned_text  if job.cover_pii  else None,
            resume_text  = job.resume_pii.cleaned_text if job.resume_pii else None,
            rec_text     = job.rec_pii.cleaned_text    if job.rec_pii    else None,
            out_dir      = OUTPUT_DIR,
        )
        job.output_path = out_path
        job.output_size = size
        self._emit(f"  PDF: {out_path.name} ({size//1024}KB)")
        return self._pause(PausePoint.PDF_PREVIEW, job)

    # ── 5단계: 원본 보관 + 기록 ──────────────────────────────────────────
    def _step_save(self, job: PipelineJob) -> bool:
        self._emit("[5/5] 원본 암호화 보관 + 시트 기록")

        # 원본 암호화 보관
        for ftype, fpath in job.files.items():
            if fpath.exists():
                dst = ORIGINALS_DIR / job.candidate_id / fpath.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(fpath), str(dst))
                encrypt_file(dst, dst.with_suffix(dst.suffix + ".enc"))
                secure_delete(dst)

        # 임시 처리 폴더 정리
        tmp_dir = PROCESSING_DIR / job.candidate_id
        if tmp_dir.exists():
            secure_delete_dir(tmp_dir)

        # 구글시트 기록
        pii_total = sum([
            len(job.cover_pii.pii_found)  if job.cover_pii  else 0,
            len(job.resume_pii.pii_found) if job.resume_pii else 0,
            len(job.rec_pii.pii_found)    if job.rec_pii    else 0,
        ])
        try:
            write_processed_entry(
                candidate_id    = job.candidate_id,
                output_filename = job.output_path.name if job.output_path else "",
                pii_count       = pii_total,
            )
        except Exception as e:
            job.warnings.append(f"시트 기록 실패: {e}")

        # 처리 로그 (PII-free)
        log_processing(
            teacher_id     = job.candidate_id,
            file_count     = len(job.files),
            status         = "completed",
            pii_removed    = pii_total,
            output_size_kb = job.output_size // 1024,
        )

        return self._pause(PausePoint.SAVE, job)

    # ── 메인 실행 ──────────────────────────────────────────────────────────
    def run(self, candidate_id: str, folder: Path) -> PipelineJob:
        """
        파이프라인 전체 실행.

        Args:
            candidate_id: 강사 번호
            folder:       분류된 파일 폴더 (inbox/{id}_제출_{날짜}/)

        Returns:
            PipelineJob (결과 포함)
        """
        job = PipelineJob(candidate_id=candidate_id)
        self._emit(f"\n{'='*40}")
        self._emit(f"파이프라인 시작: {candidate_id}")

        steps = [
            ("classify",  lambda: self._step_classify(job, folder)),
            ("face_crop", lambda: self._step_face_crop(job)),
            ("pii",       lambda: self._step_pii(job)),
            ("build_pdf", lambda: self._step_build_pdf(job)),
            ("save",      lambda: self._step_save(job)),
        ]

        for name, fn in steps:
            try:
                ok = fn()
                if not ok:
                    job.errors.append(f"{name} 취소됨")
                    log_processing(job.candidate_id, len(job.files), f"cancelled@{name}")
                    self._emit(f"파이프라인 취소: {name}")
                    return job
            except Exception as e:
                job.errors.append(f"{name} 오류: {e}")
                log.exception(f"파이프라인 오류 at {name}")
                log_processing(job.candidate_id, len(job.files), f"error@{name}")
                return job

        self._emit(f"파이프라인 완료: {job.output_path}")
        return job


# ── 텍스트 추출 헬퍼 ──────────────────────────────────────────────────────
def _extract_text(path: Path) -> str:
    """PDF / DOCX 에서 텍스트 추출."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    if ext in (".docx", ".doc"):
        try:
            from docx import Document
            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            log.warning(f"DOCX 텍스트 추출 실패: {e}")
    return ""


# ── PDF 내장 이미지에서 얼굴 사진 추출 ────────────────────────────────────
def _extract_photo_from_pdf(pdf_path: Path) -> bytes | None:
    """
    PDF 내장 이미지 중 얼굴이 감지되는 첫 번째 이미지를 크롭하여 반환.

    - 앞 3페이지만 검사 (사진은 보통 1~2페이지)
    - 크기 필터: 60~1200px (로고·배경 제외)
    - 가로형 이미지 제외 (너비 > 높이×1.5)

    Returns:
        bytes: crop_face_from_bytes() 결과 (300×400 JPEG), 없으면 None
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        log.warning("PyMuPDF 미설치 — PDF 내장 사진 추출 불가")
        return None

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        log.warning(f"PDF 열기 실패: {e}")
        return None

    result = None
    try:
        for page_num in range(min(3, len(doc))):
            page = doc[page_num]
            images = page.get_images(full=True)

            for img_info in images:
                xref = img_info[0]
                try:
                    base_img = doc.extract_image(xref)
                except Exception:
                    continue

                w = base_img.get("width",  0)
                h = base_img.get("height", 0)

                # 크기 필터: 너무 작은 아이콘 / 너무 큰 배경 / 가로형 배너 제외
                if w < 60 or h < 60:
                    continue
                if w > 1200 or h > 1200:
                    continue
                if w > h * 1.5:
                    continue

                try:
                    result = crop_face_from_bytes(base_img["image"])
                    return result   # 첫 얼굴 발견 즉시 반환
                except FaceNotFoundError:
                    continue        # 이 이미지엔 얼굴 없음
                except Exception as e:
                    log.debug(f"이미지 처리 실패 (xref={xref}): {e}")
                    continue
    finally:
        doc.close()

    return result


# ── CLI ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("사용법: python pipeline.py <강사번호> <폴더경로>")
        sys.exit(1)

    pl = Pipeline(auto_mode=True)
    job = pl.run(sys.argv[1], Path(sys.argv[2]))
    print(f"\n결과: {job.output_path}")
    if job.errors:
        print(f"오류: {job.errors}")
    if job.warnings:
        print(f"경고: {job.warnings}")
