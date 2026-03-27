"""
file_classifier.py — BRIDGE Resume Converter
홈페이지 제출 파일 강사별 자동 구분 + watchdog 감시

우선순위:
  1순위: 파일명에 번호 포함 (예: 3126_resume.docx)
  2순위: 제출 시각 기준 10분 이내 도착 파일 묶기
  3순위: 구글시트 D열 최신 미처리 번호와 매칭
"""

from __future__ import annotations

import os
import re
import shutil
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ── 기본 경로 ──────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent
INBOX_DIR = BASE_DIR / "inbox"
LOGS_DIR  = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# ── 로거 설정 ──────────────────────────────────────────────────────────────
logging.basicConfig(
    filename=str(LOGS_DIR / "classifier.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
log = logging.getLogger("file_classifier")

# ── 파일 타입 판별 규칙 ────────────────────────────────────────────────────
PHOTO_EXTS   = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp"}
DOC_EXTS     = {".pdf", ".docx", ".doc"}
PHOTO_SIZE_MAX = 5 * 1024 * 1024  # 5MB

def detect_file_type(path: Path) -> str:
    """파일 타입 자동 판별: photo / resume / cover / rec / unknown"""
    ext  = path.suffix.lower()
    name = path.stem.lower()

    if ext in PHOTO_EXTS:
        try:
            if path.exists() and path.stat().st_size >= PHOTO_SIZE_MAX:
                return "unknown"  # 사진이지만 너무 큼
        except Exception:
            pass
        return "photo"

    if ext in DOC_EXTS:
        if re.search(r"(cover|cover_letter|coverletter)", name):
            return "cover"
        if re.search(r"(recommend|reference|ref_letter|letter_of_rec|^rec_|_rec_|_rec$)", name):
            return "rec"
        if re.search(r"(resume|cv|curriculum)", name):
            return "resume"
        # 확장자만으로는 알 수 없으면 resume 기본값
        return "resume"

    return "unknown"


# ── 번호 추출 ──────────────────────────────────────────────────────────────
_NUM_RE = re.compile(r"(?<!\d)(\d{4,6})(?!\d)")

def extract_number(filename: str) -> Optional[str]:
    """파일명에서 강사번호(4~6자리) 추출. 없으면 None."""
    m = _NUM_RE.search(filename)
    return m.group(1) if m else None


# ── 분류 기록 저장소 (10분 창 묶기용) ─────────────────────────────────────
_recent: dict[str, list[tuple[float, Path]]] = {}  # {number: [(ts, path), ...]}
_WINDOW_SECS = 600  # 10분

def _prune_recent():
    cutoff = time.time() - _WINDOW_SECS
    for num in list(_recent.keys()):
        _recent[num] = [(ts, p) for ts, p in _recent[num] if ts > cutoff]
        if not _recent[num]:
            del _recent[num]


# ── 중복/재지원 감지 ────────────────────────────────────────────────────────
_DUPLICATE_DAYS  = 7
_REAPPLY_DAYS    = 30

def _check_duplicate_reapply(
    number: str,
    callback_dup: Callable | None = None,
    callback_reapply: Callable | None = None,
):
    """
    같은 번호의 기존 폴더를 확인하여 중복/재지원 감지.
    callback_dup(number, old_path, new_path) — 7일 이내
    callback_reapply(number, old_path)       — 30일 이상
    """
    pattern = re.compile(rf"^{re.escape(number)}_제출_")
    existing = [d for d in INBOX_DIR.iterdir()
                if d.is_dir() and pattern.match(d.name)]
    if not existing:
        return

    for old_dir in existing:
        m = re.search(r"(\d{8})", old_dir.name)
        if not m:
            continue
        old_date = datetime.strptime(m.group(1), "%Y%m%d")
        delta    = (datetime.now() - old_date).days

        if delta <= _DUPLICATE_DAYS and callback_dup:
            callback_dup(number, old_dir, None)
        elif delta >= _REAPPLY_DAYS and callback_reapply:
            callback_reapply(number, old_dir)


# ── 핵심 분류 함수 ─────────────────────────────────────────────────────────
def classify_file(
    src_path: Path,
    sheets_get_latest_unprocessed: Callable | None = None,
    on_unknown: Callable | None = None,
    on_duplicate: Callable | None = None,
    on_reapply: Callable | None = None,
) -> Optional[Path]:
    """
    src_path 파일을 분류하여 inbox/{number}_제출_{날짜}/ 로 이동.
    반환값: 이동된 목적 경로 (실패 시 None)
    """
    if not src_path.exists():
        return None

    # 짧게 대기 (파일 쓰기 완료 보장)
    time.sleep(0.3)

    fname  = src_path.name
    ftype  = detect_file_type(src_path)
    now_ts = time.time()
    today  = datetime.now().strftime("%Y%m%d")

    # ── 1순위: 파일명 번호 ───────────────────────────────────────────────
    number = extract_number(fname)

    # ── 2순위: 최근 10분 창 묶기 ────────────────────────────────────────
    if not number:
        _prune_recent()
        # 가장 최근에 온 번호 그룹에 붙이기
        if _recent:
            # 가장 최근 ts의 그룹 선택
            best_num = max(_recent, key=lambda k: max(ts for ts, _ in _recent[k]))
            number   = best_num
        else:
            number = "unknown"

    # ── 3순위: 시트에서 최신 미처리 번호 ────────────────────────────────
    if number == "unknown" and sheets_get_latest_unprocessed:
        try:
            num_from_sheet = sheets_get_latest_unprocessed()
            if num_from_sheet:
                number = str(num_from_sheet)
        except Exception as e:
            log.warning(f"시트 조회 실패: {e}")

    # ── 중복/재지원 감지 ──────────────────────────────────────────────────
    _check_duplicate_reapply(number, on_duplicate, on_reapply)

    # ── 대상 폴더 결정 ─────────────────────────────────────────────────────
    if number == "unknown":
        dest_dir = INBOX_DIR / "unknown"
        if on_unknown:
            on_unknown(src_path, ftype)
    else:
        dest_dir = INBOX_DIR / f"{number}_제출_{today}"

    dest_dir.mkdir(parents=True, exist_ok=True)

    # 파일명 중복 방지
    dest_path = dest_dir / fname
    if dest_path.exists():
        stem = src_path.stem
        ext  = src_path.suffix
        ts_s = datetime.now().strftime("%H%M%S")
        dest_path = dest_dir / f"{stem}_{ts_s}{ext}"

    shutil.move(str(src_path), str(dest_path))

    # 최근 기록 갱신
    if number != "unknown":
        _recent.setdefault(number, []).append((now_ts, dest_path))

    log.info(f"분류완료: {fname} → {dest_dir.name} / 타입={ftype}")
    return dest_path


# ── Watchdog 핸들러 ────────────────────────────────────────────────────────
class InboxHandler(FileSystemEventHandler):
    """inbox\ 폴더 감시 → 새 파일 감지 시 자동 분류"""

    def __init__(
        self,
        sheets_get_fn:    Callable | None = None,
        on_unknown_fn:    Callable | None = None,
        on_duplicate_fn:  Callable | None = None,
        on_reapply_fn:    Callable | None = None,
    ):
        self._sheets_fn    = sheets_get_fn
        self._on_unknown   = on_unknown_fn
        self._on_duplicate = on_duplicate_fn
        self._on_reapply   = on_reapply_fn

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        # 숨김 파일·임시 파일 무시
        if path.name.startswith((".", "~", "_tmp")):
            return
        log.info(f"새 파일 감지: {path.name}")
        try:
            classify_file(
                path,
                self._sheets_fn,
                self._on_unknown,
                self._on_duplicate,
                self._on_reapply,
            )
        except Exception as e:
            log.error(f"분류 오류 {path.name}: {e}")


# ── 감시 시작/중지 ─────────────────────────────────────────────────────────
_observer: Optional[Observer] = None

def start_watcher(
    sheets_get_fn:    Callable | None = None,
    on_unknown_fn:    Callable | None = None,
    on_duplicate_fn:  Callable | None = None,
    on_reapply_fn:    Callable | None = None,
) -> Observer:
    """inbox\ 폴더 watchdog 감시 시작."""
    global _observer
    INBOX_DIR.mkdir(exist_ok=True)
    handler   = InboxHandler(sheets_get_fn, on_unknown_fn, on_duplicate_fn, on_reapply_fn)
    _observer = Observer()
    _observer.schedule(handler, str(INBOX_DIR), recursive=False)
    _observer.start()
    log.info("watcher 시작")
    return _observer

def stop_watcher():
    global _observer
    if _observer and _observer.is_alive():
        _observer.stop()
        _observer.join()
        log.info("watcher 중지")
    _observer = None


# ── CLI 테스트 ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        result = classify_file(p)
        print(f"분류 결과: {result}")
    else:
        print("watchdog 감시 모드 시작 (Ctrl+C로 중지)")
        obs = start_watcher()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_watcher()
