"""
BRIDGE Google Drive Auto Backup System (G: Drive Direct Copy)

Strategy: Copy files to G:\\BRIDGE_Backups\\ (Google Drive already mounted as G:)
Google Drive Backup & Sync will handle the actual cloud sync automatically.
No API key or quota issues.

Backup targets:
  1. master.db (SQLite) -- daily full dump
  2. Original resumes/cover letters -- new files only
  3. Converted resume PDFs (PII-removed) -- new files only
  4. Video files (mp4/mov intro videos) -- new files only
  5. Employer-related documents -- new files only
  6. Config files (excl. .env) -- daily snapshot

Backup location:
  G:\\BRIDGE_Backups\\       (auto-created)
  |-- db/         <- master.db YYYYMMDD.db
  |-- originals/  <- original resumes/cover letters
  |-- resumes/    <- converted resume PDFs (PII-removed)
  |-- videos/     <- intro videos (mp4/mov)
  |-- employers/  <- employer documents
  |-- config/     <- YYYYMMDD_<filename> snapshots

Usage:
  python tools/gdrive_backup.py --all
  python tools/gdrive_backup.py --db
  python tools/gdrive_backup.py --resumes
  python tools/gdrive_backup.py --config
"""
import os
import sys
import json
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Force UTF-8 output on Windows CP949 terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bridge.gdrive")

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
BASE_DIR    = Path("Q:/Claudework/bridge base")
DB_PATH     = BASE_DIR / "master.db"
GDRIVE_ROOT = Path("G:/BRIDGE_Backups")          # Google Drive mounted as G:
BACKUP_RECORD = BASE_DIR / "tools" / ".gdrive_backup_state.json"

# ---------------------------------------------------------------------------
# DIRECTORY LISTS  (missing dirs are silently skipped at runtime)
# ---------------------------------------------------------------------------
ORIGINAL_DIRS = [
    BASE_DIR / "tools" / "processed_docs" / "originals",  # 30 files
    BASE_DIR / "tools" / "processed_docs" / "incoming",   # 6 files
    BASE_DIR / "uploads",
    # tools/resume_converter/input -- does not exist yet (future)
]

RESUME_DIRS = [
    BASE_DIR / "tools" / "processed_docs" / "processed",  # 2 PDFs
    BASE_DIR / "tools" / "resume_converter" / "output",   # 1 PDF
]

VIDEO_DIRS = [
    BASE_DIR / "tools" / "processed_docs" / "originals",
    BASE_DIR / "tools" / "processed_docs" / "incoming",
    BASE_DIR / "uploads",
]
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".webm", ".mkv"}

EMPLOYER_DIRS = [
    BASE_DIR / "tools" / "employer_docs",   # does not exist yet (future)
    BASE_DIR / "employer_data",              # does not exist yet (future)
]

CONFIG_FILES = [
    "render.yaml",
    "CLAUDE.md",
    "requirements.txt",
    "package.json",
]

DB_KEEP_DAYS     = 30
CONFIG_KEEP_DAYS = 90


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_state() -> dict:
    if BACKUP_RECORD.exists():
        try:
            return json.loads(BACKUP_RECORD.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "uploaded_originals": [],
        "uploaded_resumes": [],
        "uploaded_videos": [],
        "uploaded_employers": [],
    }


def _save_state(state: dict) -> None:
    BACKUP_RECORD.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _copy_file(src: Path, dest_dir: Path, dest_name: str = None) -> bool:
    """Copy src to dest_dir/<dest_name>. Skip if already exists."""
    dest_name = dest_name or src.name
    dest = dest_dir / dest_name
    if dest.exists():
        logger.info("  skip (exists): %s", dest_name)
        return False
    shutil.copy2(str(src), str(dest))
    logger.info("  copied: %s", dest_name)
    return True


def _check_gdrive() -> bool:
    """Verify G: drive is accessible."""
    if not Path("G:/").exists():
        logger.error("G: drive not accessible -- Google Drive may not be running")
        return False
    return True


# ---------------------------------------------------------------------------
# BACKUP FUNCTIONS
# ---------------------------------------------------------------------------
def backup_db() -> None:
    """master.db -> G:\\BRIDGE_Backups\\db\\  (dated, 30-day cleanup)."""
    if not DB_PATH.exists():
        logger.warning("master.db not found: %s", DB_PATH)
        return

    dest_dir = _ensure_dir(GDRIVE_ROOT / "db")
    today    = datetime.now().strftime("%Y%m%d")
    dest_name = f"master_{today}.db"

    # Copy (WAL-safe: copy2 on SQLite WAL is safe for read-only backup)
    dest = dest_dir / dest_name
    if dest.exists():
        logger.info("  skip (exists): %s", dest_name)
    else:
        shutil.copy2(str(DB_PATH), str(dest))
        kb = dest.stat().st_size // 1024
        logger.info("  copied: %s (%d KB)", dest_name, kb)

    # Remove DB backups older than 30 days
    cutoff = (datetime.now() - timedelta(days=DB_KEEP_DAYS)).strftime("%Y%m%d")
    deleted = 0
    for f in dest_dir.glob("master_*.db"):
        try:
            date_part = f.stem.replace("master_", "")[:8]
            if date_part < cutoff:
                f.unlink()
                deleted += 1
        except Exception:
            pass
    if deleted:
        logger.info("  cleaned: %d old DB backups (>%dd)", deleted, DB_KEEP_DAYS)

    logger.info("DB backup done: %s", dest_name)


def backup_originals() -> None:
    """Original resumes/cover letters -> G:\\BRIDGE_Backups\\originals\\ (new only)."""
    dest_dir = _ensure_dir(GDRIVE_ROOT / "originals")
    state    = _load_state()
    uploaded = set(state.get("uploaded_originals", []))
    new_count = 0

    for d in ORIGINAL_DIRS:
        if not d.exists():
            continue
        for f in d.iterdir():
            if not f.is_file() or f.name.startswith("."):
                continue
            if f.suffix.lower() in VIDEO_EXTS:
                continue  # videos handled separately
            if f.name in uploaded:
                continue
            if _copy_file(f, dest_dir):
                new_count += 1
            uploaded.add(f.name)

    state["uploaded_originals"] = list(uploaded)
    _save_state(state)
    logger.info("Originals backup done: %d new, %d total", new_count, len(uploaded))


def backup_resumes() -> None:
    """Converted PDF resumes -> G:\\BRIDGE_Backups\\resumes\\ (new only)."""
    dest_dir  = _ensure_dir(GDRIVE_ROOT / "resumes")
    state     = _load_state()
    uploaded  = set(state.get("uploaded_resumes", []))
    new_count = 0

    for d in RESUME_DIRS:
        if not d.exists():
            continue
        for pdf in d.glob("*.pdf"):
            if pdf.name in uploaded:
                continue
            if _copy_file(pdf, dest_dir):
                new_count += 1
            uploaded.add(pdf.name)

    state["uploaded_resumes"] = list(uploaded)
    _save_state(state)
    logger.info("Resumes backup done: %d new, %d total", new_count, len(uploaded))


def backup_videos() -> None:
    """Video files -> G:\\BRIDGE_Backups\\videos\\ (new only)."""
    dest_dir  = _ensure_dir(GDRIVE_ROOT / "videos")
    state     = _load_state()
    uploaded  = set(state.get("uploaded_videos", []))
    new_count = 0

    for d in VIDEO_DIRS:
        if not d.exists():
            continue
        for f in d.iterdir():
            if not f.is_file():
                continue
            if f.suffix.lower() not in VIDEO_EXTS:
                continue
            if f.name in uploaded:
                continue
            if _copy_file(f, dest_dir):
                new_count += 1
            uploaded.add(f.name)

    state["uploaded_videos"] = list(uploaded)
    _save_state(state)
    logger.info("Videos backup done: %d new, %d total", new_count, len(uploaded))


def backup_employers() -> None:
    """Employer docs -> G:\\BRIDGE_Backups\\employers\\ (new only, recursive)."""
    dest_dir  = _ensure_dir(GDRIVE_ROOT / "employers")
    state     = _load_state()
    uploaded  = set(state.get("uploaded_employers", []))
    new_count = 0

    for d in EMPLOYER_DIRS:
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if not f.is_file() or f.name.startswith("."):
                continue
            rel = str(f.relative_to(d)).replace("\\", "/")
            if rel in uploaded:
                continue
            if _copy_file(f, dest_dir):
                new_count += 1
            uploaded.add(rel)

    state["uploaded_employers"] = list(uploaded)
    _save_state(state)
    logger.info("Employers backup done: %d new, %d total", new_count, len(uploaded))


def backup_config() -> None:
    """Config files -> G:\\BRIDGE_Backups\\config\\ (YYYYMMDD_<name>)."""
    dest_dir = _ensure_dir(GDRIVE_ROOT / "config")
    today    = datetime.now().strftime("%Y%m%d")
    copied   = 0

    for fname in CONFIG_FILES:
        src = BASE_DIR / fname
        if not src.exists():
            continue
        if _copy_file(src, dest_dir, f"{today}_{fname}"):
            copied += 1

    # Remove config snapshots older than 90 days
    cutoff = (datetime.now() - timedelta(days=CONFIG_KEEP_DAYS)).strftime("%Y%m%d")
    deleted = 0
    for f in dest_dir.iterdir():
        if not f.is_file():
            continue
        try:
            date_part = f.name[:8]
            if len(date_part) == 8 and date_part < cutoff:
                f.unlink()
                deleted += 1
        except Exception:
            pass
    if deleted:
        logger.info("  cleaned: %d old config backups (>%dd)", deleted, CONFIG_KEEP_DAYS)

    logger.info("Config backup done: %d new", copied)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="BRIDGE Google Drive backup (G: drive)")
    parser.add_argument("--all",       action="store_true", help="Full backup")
    parser.add_argument("--db",        action="store_true", help="DB only")
    parser.add_argument("--originals", action="store_true", help="Original resumes only")
    parser.add_argument("--resumes",   action="store_true", help="Converted PDFs only")
    parser.add_argument("--videos",    action="store_true", help="Videos only")
    parser.add_argument("--employers", action="store_true", help="Employer docs only")
    parser.add_argument("--config",    action="store_true", help="Config only")
    args = parser.parse_args()

    if not any([
        args.all, args.db, args.originals, args.resumes,
        args.videos, args.employers, args.config,
    ]):
        args.all = True

    if not _check_gdrive():
        sys.exit(1)

    logger.info("Backup target: %s", GDRIVE_ROOT)

    if args.all or args.db:
        backup_db()
    if args.all or args.originals:
        backup_originals()
    if args.all or args.resumes:
        backup_resumes()
    if args.all or args.videos:
        backup_videos()
    if args.all or args.employers:
        backup_employers()
    if args.all or args.config:
        backup_config()

    logger.info("=== Backup complete -> %s", GDRIVE_ROOT)


if __name__ == "__main__":
    main()
