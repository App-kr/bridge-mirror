# -*- coding: utf-8 -*-
"""
session-end-backup.py
세션 종료 시 Claude Code가 실행하는 백업 스크립트

사용법:
  python tools/session-end-backup.py "오늘 한 작업 요약"
"""
import io
import os
import sys
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Windows 콘솔 UTF-8 강제
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE = Path("Q:/Claudework/bridge base")
BACKUPS = BASE / ".backups"
DAYS = ["일", "월", "화", "수", "목", "금", "토"]

def run(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True,  # nosec B602 B603 B604 B605 B607
                                encoding="utf-8", cwd=str(BASE))
        return result.stdout.strip()
    except Exception:
        return ""

def main():
    note = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "(내용 없음)"
    now = datetime.now()
    dow = DAYS[now.weekday()]   # 월=0 ... 일=6
    label = now.strftime("%Y-%m-%d") + f"_{dow}"
    dest = BACKUPS / label

    print(f"📦 백업 시작: {label}")
    dest.mkdir(parents=True, exist_ok=True)

    # 1. .memory 폴더 복사
    mem_src = BASE / ".memory"
    if mem_src.exists():
        shutil.copytree(mem_src, dest / "memory", dirs_exist_ok=True)
        print("  ✓ .memory 복사")

    # 2. git log 저장
    git_log = run("git log --oneline -20")
    (dest / "git-log.txt").write_text(git_log, encoding="utf-8")
    print("  ✓ git-log.txt")

    # 3. 오늘 변경 파일 목록
    changed = run("git diff --name-only HEAD~5 HEAD 2>nul")
    (dest / "changed-files.txt").write_text(changed, encoding="utf-8")
    print("  ✓ changed-files.txt")

    # 4. 세션 노트
    session_note = f"""# 세션 노트 — {label}

## 작업 요약
{note}

## 생성 시각
{now.strftime('%Y-%m-%d %H:%M:%S')}
"""
    (dest / "session-note.md").write_text(session_note, encoding="utf-8")
    print("  ✓ session-note.md")

    # 5. daily-log.md 업데이트
    daily_log = BASE / ".memory" / "daily-log.md"
    log_entry = f"""## [{now.strftime('%Y-%m-%d')} {dow}요일 {now.strftime('%H:%M')}] 세션 종료
### 완료한 작업
{note}
### 내일 이어서
- (다음 세션에서 확인)
### 백업 위치
- `.backups/{label}/`
---

"""
    if daily_log.exists():
        existing = daily_log.read_text(encoding="utf-8")
        # 헤더 다음에 삽입
        lines = existing.split("\n", 3)
        header = "\n".join(lines[:3]) + "\n\n" if len(lines) >= 3 else existing
        rest = lines[3] if len(lines) > 3 else ""
        daily_log.write_text(header + log_entry + rest, encoding="utf-8")
    else:
        daily_log.write_text("# BRIDGE 일일 작업 로그\n\n" + log_entry, encoding="utf-8")
    print("  ✓ daily-log.md 업데이트")

    # 6. 14일 이전 폴더 삭제
    cutoff = datetime.now() - timedelta(days=14)
    for old in BACKUPS.iterdir():
        if old.is_dir():
            try:
                date_str = old.name[:10]
                old_date = datetime.strptime(date_str, "%Y-%m-%d")
                if old_date < cutoff:
                    shutil.rmtree(old)
                    print(f"  🗑 14일 초과 삭제: {old.name}")
            except Exception:
                pass

    print(f"\n✅ 백업 완료: {dest}")
    print(f"   14일치 보관 중")

    # 7. Notion 일일 기록 (하루 마지막 백업에만)
    notion_log = BASE / "tools" / "notion_daily_log.py"
    if notion_log.exists():
        print("\n📓 Notion 기록 중...")
        r = subprocess.run(
            [sys.executable, "-X", "utf8", str(notion_log), note],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(BASE)
        )
        if r.returncode == 0:
            for line in r.stdout.splitlines():
                if line.strip():
                    print(" ", line.strip())
        else:
            print("  [Notion] 실패 (토큰 미설정이면 무시)")

if __name__ == "__main__":
    main()
