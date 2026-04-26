"""
github_release_backup.py — master.db.enc → GitHub Releases 업로드

목적: workflow scope 없는 PAT 로도 동작하는 클라우드 이중화 백업.
       (기존 weekly-encrypted-backup.yml 워크플로우와 동일 목표를 로컬에서 처리)

사용법:
  "Q:/Phtyon 3/python.exe" -X utf8 scripts/github_release_backup.py
  "Q:/Phtyon 3/python.exe" -X utf8 scripts/github_release_backup.py --keep-days 30

동작:
  1. master.db.enc 존재 확인 (없으면 db_backup_enc.py encrypt 자동 호출)
  2. 일자 태그(db-backup-YYYY-MM-DD) 릴리스 생성 또는 갱신
  3. master.db.enc + master.db.enc.meta 자산 업로드
  4. keep-days 일 이전 db-backup-* 릴리스 자동 삭제

전제:
  - gh CLI 인증 (repo scope)
  - tools/db_backup_enc.py 정상 동작 (BRIDGE_FIELD_KEY)

릴리스는 모두 .enc 파일 — 평문 절대 push 없음.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ENC = BASE / "master.db.enc"
META = BASE / "master.db.enc.meta"
PYTHON = os.environ.get("BRIDGE_PYTHON", r"Q:\Phtyon 3\python.exe")
TAG_PATTERN = re.compile(r"^db-backup-(\d{4}-\d{2}-\d{2})$")


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


def ensure_enc() -> bool:
    """master.db.enc 가 없거나 24시간 이상 묵었으면 재생성."""
    need = False
    if not ENC.exists():
        log("master.db.enc 없음 → 새로 생성")
        need = True
    else:
        age = datetime.now() - datetime.fromtimestamp(ENC.stat().st_mtime)
        if age > timedelta(hours=24):
            log(f"master.db.enc 갱신 필요 ({age})")
            need = True

    if not need:
        return True

    # BRIDGE_FIELD_KEY 자동 로드
    try:
        sys.path.insert(0, str(BASE / "tools"))
        import bx
        bx.load_to_env()
    except Exception as e:
        log(f"⚠ BX 로드 실패: {e}")

    if not os.environ.get("BRIDGE_FIELD_KEY"):
        log("❌ BRIDGE_FIELD_KEY 없음 — 암호화 불가")
        return False

    p = run([PYTHON, "-X", "utf8", str(BASE / "tools" / "db_backup_enc.py"), "encrypt"],
            cwd=str(BASE), env=os.environ.copy())
    if p.returncode != 0:
        log(f"❌ encrypt 실패: {p.stderr[:300]}")
        return False
    log("✅ master.db.enc 갱신")
    return True


def upsert_release(tag: str, title: str, notes: str) -> bool:
    """태그 릴리스가 있으면 자산 갱신, 없으면 새로 생성."""
    p = run(["gh", "release", "view", tag, "--json", "tagName"], cwd=str(BASE))
    exists = p.returncode == 0

    if not exists:
        log(f"새 릴리스 생성: {tag}")
        p = run(
            ["gh", "release", "create", tag, "--title", title, "--notes", notes,
             str(ENC), str(META)],
            cwd=str(BASE),
        )
        if p.returncode != 0:
            log(f"❌ create 실패: {p.stderr[:300]}")
            return False
        log("  ✅ 릴리스 + 자산 업로드 완료")
        return True

    log(f"기존 릴리스 자산 갱신: {tag}")
    # clobber로 같은 이름 자산 덮어쓰기
    p = run(
        ["gh", "release", "upload", tag, str(ENC), str(META), "--clobber"],
        cwd=str(BASE),
    )
    if p.returncode != 0:
        log(f"❌ upload 실패: {p.stderr[:300]}")
        return False
    log("  ✅ 자산 갱신 완료")
    return True


def cleanup_old(keep_days: int) -> None:
    """db-backup-YYYY-MM-DD 릴리스 중 keep_days 이전 자동 삭제."""
    p = run(["gh", "release", "list", "--limit", "200", "--json", "tagName,createdAt"], cwd=str(BASE))
    if p.returncode != 0:
        log(f"⚠ list 실패 (skip cleanup): {p.stderr[:200]}")
        return
    try:
        rels = json.loads(p.stdout)
    except json.JSONDecodeError:
        log("⚠ list JSON 파싱 실패")
        return

    cutoff = datetime.now() - timedelta(days=keep_days)
    deleted = 0
    for r in rels:
        tag = r.get("tagName", "")
        m = TAG_PATTERN.match(tag)
        if not m:
            continue
        try:
            tag_date = datetime.strptime(m.group(1), "%Y-%m-%d")
        except ValueError:
            continue
        if tag_date >= cutoff:
            continue
        log(f"  삭제: {tag} ({(datetime.now() - tag_date).days}일 경과)")
        run(["gh", "release", "delete", tag, "-y", "--cleanup-tag"], cwd=str(BASE))
        deleted += 1
    if deleted:
        log(f"  ✅ {deleted}개 릴리스 정리")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-days", type=int, default=30, help="이 일수 이전 백업 자동 삭제")
    ap.add_argument("--skip-cleanup", action="store_true")
    args = ap.parse_args()

    log("=" * 60)
    log("github_release_backup 시작")

    # gh CLI 확인
    p = run(["gh", "auth", "status"], cwd=str(BASE))
    if p.returncode != 0:
        log("❌ gh CLI 미인증 — `gh auth login` 먼저 실행")
        return 1

    if not ensure_enc():
        return 1

    today = datetime.now().strftime("%Y-%m-%d")
    tag = f"db-backup-{today}"
    title = f"DB Backup {today}"
    notes = (
        "Encrypted master.db (AES-256-GCM, PBKDF2-600k).\n\n"
        "Decrypt: `python tools/db_backup_enc.py decrypt` (BRIDGE_FIELD_KEY required).\n\n"
        f"Created by github_release_backup.py at {datetime.now().isoformat()}"
    )

    if not upsert_release(tag, title, notes):
        return 1

    if not args.skip_cleanup:
        cleanup_old(args.keep_days)

    log("✅ 전체 성공")
    return 0


if __name__ == "__main__":
    sys.exit(main())
