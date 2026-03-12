#!/usr/bin/env python3
"""
BRIDGE Backup System v3.0
- 매 작업 시작 전 자동 타임스탬프 스냅샷
- 작업명 기록 → 롤백 가능한 독립 백업본
- CLAUDE.md PreToolUse 훅과 연동
- 덮어쓰기 절대 금지: 모든 백업은 신규 디렉토리
"""

import os
import sys
import json
import shutil
import hashlib
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# ── 경로 설정
BASE     = Path(r"Q:\Claudework\bridge base")
BACKUP   = BASE / "backups"
LOG_FILE = Path(r"Q:\Obsidian\Scarlett\BRIDGE_백업일지.md")
STATE_F  = BASE / "tools" / "backup_state.json"

# ── 백업 대상 (git-tracked + critical non-tracked)
TARGETS = [
    "api_server.py",
    "master.db",
    ".env",
    "CLAUDE.md",
    ".claude/settings.json",
    "render.yaml",
    "requirements.txt",
    "web_frontend/src",
    "tools",
    "docs/obsidian",
]

EXCLUDE_PATTERNS = {
    "__pycache__", "node_modules", ".next", "*.pyc",
    "*.tsbuildinfo", ".git", "backups"
}


def ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ts_human() -> str:
    return datetime.now().strftime("%Y.%m.%d %H:%M:%S")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()[:12]
    except Exception:
        return "??????"


def git_head() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=BASE, capture_output=True, text=True
        )
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def git_status_summary() -> str:
    try:
        r = subprocess.run(
            ["git", "status", "--short"],
            cwd=BASE, capture_output=True, text=True
        )
        lines = r.stdout.strip().splitlines()
        return f"{len(lines)}개 변경" if lines else "clean"
    except Exception:
        return "unknown"


_WIN_RESERVED = {"nul", "con", "prn", "aux", "com1", "com2", "com3", "com4",
                  "com5", "com6", "com7", "com8", "com9", "lpt1", "lpt2",
                  "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9"}

def should_exclude(path: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDE_PATTERNS:
            return True
        if part.lower() in _WIN_RESERVED:  # Windows 예약 디바이스명 제외
            return True
    for pat in EXCLUDE_PATTERNS:
        if "*" in pat and path.match(pat):
            return True
    return False


def copy_target(src: Path, dst_root: Path) -> dict:
    result = {"files": 0, "size": 0, "errors": []}
    if not src.exists():
        result["errors"].append(f"NOT FOUND: {src}")
        return result

    if src.is_file():
        dst = dst_root / src.relative_to(BASE)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        result["files"] += 1
        result["size"] += src.stat().st_size
    elif src.is_dir():
        for item in src.rglob("*"):
            if should_exclude(item):
                continue
            if item.is_file():
                dst = dst_root / item.relative_to(BASE)
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(item, dst)
                    result["files"] += 1
                    result["size"] += item.stat().st_size
                except Exception as e:
                    result["errors"].append(str(e))
    return result


def create_backup(task_name: str, task_type: str = "manual") -> dict:
    """
    새 타임스탬프 디렉토리 생성 → 덮어쓰기 절대 없음
    backups/YYYYMMDD_HHMMSS__작업명/
    """
    BACKUP.mkdir(parents=True, exist_ok=True)

    safe_name = task_name.replace(" ", "_").replace("/", "-")[:60]
    snapshot_dir = BACKUP / f"{ts()}__{safe_name}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # 백업 실행
    total_files = 0
    total_size  = 0
    all_errors  = []

    for target_rel in TARGETS:
        src = BASE / target_rel
        r = copy_target(src, snapshot_dir)
        total_files += r["files"]
        total_size  += r["size"]
        all_errors  += r["errors"]

    # DB sha256
    db_hash = sha256_file(BASE / "master.db")

    # 메타데이터 저장
    meta = {
        "timestamp"  : ts_human(),
        "task_name"  : task_name,
        "task_type"  : task_type,
        "git_head"   : git_head(),
        "git_status" : git_status_summary(),
        "total_files": total_files,
        "total_size" : total_size,
        "db_hash"    : db_hash,
        "errors"     : all_errors,
        "snapshot_dir": str(snapshot_dir),
    }
    (snapshot_dir / "_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # state 업데이트
    state = load_state()
    state.setdefault("backups", []).append({
        "dir"      : snapshot_dir.name,
        "task"     : task_name,
        "ts"       : ts_human(),
        "git"      : git_head(),
        "files"    : total_files,
        "db_hash"  : db_hash,
    })
    state["last_backup"] = ts_human()
    state["total_count"] = len(state["backups"])
    save_state(state)

    # 작업일지 기록
    append_log(meta)

    # 오래된 백업 정리 (30개 초과 시 오래된 것 삭제)
    cleanup_old_backups(keep=30)

    return meta


def append_log(meta: dict):
    """BRIDGE_백업일지.md에 신규 항목 추가 (append only)"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not LOG_FILE.exists():
        LOG_FILE.write_text(
            "# BRIDGE 백업 일지\n\n> 자동 생성 — bridge_backup.py v3.0\n\n---\n\n",
            encoding="utf-8"
        )

    errors_md = ""
    if meta["errors"]:
        errors_md = "\n  - ⚠️ 오류: " + ", ".join(meta["errors"][:3])

    entry = (
        f"### {meta['timestamp']} — {meta['task_name']}\n"
        f"- 유형: `{meta['task_type']}`\n"
        f"- Git HEAD: `{meta['git_head']}` ({meta['git_status']})\n"
        f"- 파일 수: {meta['total_files']}개 / {meta['total_size']//1024}KB\n"
        f"- DB SHA256: `{meta['db_hash']}`\n"
        f"- 경로: `{Path(meta['snapshot_dir']).name}`"
        f"{errors_md}\n\n"
    )

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def load_state() -> dict:
    if STATE_F.exists():
        try:
            return json.loads(STATE_F.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"backups": [], "last_backup": None, "total_count": 0}


def save_state(state: dict):
    STATE_F.parent.mkdir(parents=True, exist_ok=True)
    STATE_F.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def cleanup_old_backups(keep: int = 30):
    """오래된 백업 디렉토리 삭제 (keep 개수 유지)"""
    dirs = sorted(
        [d for d in BACKUP.iterdir() if d.is_dir() and not d.name.startswith("_")],
        key=lambda d: d.name
    )
    if len(dirs) > keep:
        for old in dirs[:len(dirs) - keep]:
            try:
                shutil.rmtree(old)
                print(f"  [cleanup] 삭제: {old.name}")
            except Exception as e:
                print(f"  [cleanup] 실패: {old.name} — {e}")


def list_backups(n: int = 10):
    state = load_state()
    backups = state.get("backups", [])
    print(f"\n{'='*60}")
    print(f"BRIDGE 백업 목록 (최근 {n}개 / 전체 {len(backups)}개)")
    print(f"{'='*60}")
    for b in backups[-n:]:
        print(f"  {b['ts']}  [{b['git']}]  {b['task']}")
        print(f"    └─ {b['dir']}  ({b['files']}파일, DB:{b['db_hash']})")
    print()


def rollback(snapshot_name: str, dry_run: bool = False):
    """특정 스냅샷으로 롤백"""
    snap = BACKUP / snapshot_name
    if not snap.exists():
        print(f"❌ 스냅샷 없음: {snapshot_name}")
        sys.exit(1)

    meta_file = snap / "_meta.json"
    meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}

    print(f"\n{'='*60}")
    print(f"ROLLBACK: {snapshot_name}")
    print(f"  작업명: {meta.get('task_name', '?')}")
    print(f"  시간:   {meta.get('timestamp', '?')}")
    print(f"  Git:    {meta.get('git_head', '?')}")
    if dry_run:
        print("  [DRY RUN — 실제 적용 안 함]")
        return

    confirm = input("  ⚠️  실제 롤백 진행? (yes 입력): ").strip()
    if confirm != "yes":
        print("  취소됨.")
        return

    # 롤백 전 현재 상태 자동 백업
    print("  → 현재 상태 자동 백업 중...")
    create_backup(f"rollback_before_{snapshot_name[:20]}", task_type="auto-pre-rollback")

    # 파일 복원
    for item in snap.rglob("*"):
        if item.name == "_meta.json":
            continue
        if item.is_file():
            rel = item.relative_to(snap)
            dst = BASE / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dst)

    print(f"  ✅ 롤백 완료: {snapshot_name}")


def register_hook():
    """
    CLAUDE.md PreToolUse 훅 등록:
    모든 파일 수정 도구 실행 전 bridge_backup.py --pre-hook 자동 호출
    """
    settings_file = BASE / ".claude" / "settings.json"
    settings_file.parent.mkdir(parents=True, exist_ok=True)

    if settings_file.exists():
        settings = json.loads(settings_file.read_text(encoding="utf-8"))
    else:
        settings = {}

    py = sys.executable
    script = str(BASE / "tools" / "bridge_backup.py")

    hook_cmd = f'"{py}" "{script}" --pre-hook "$CLAUDE_TOOL_NAME"'

    hooks = settings.setdefault("hooks", [])

    # 중복 방지
    hooks = [h for h in hooks if "bridge_backup" not in str(h)]

    hooks.append({
        "matcher": ".*",
        "hooks": [{
            "type"   : "command",
            "command": hook_cmd
        }]
    })
    settings["hooks"] = hooks

    settings_file.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"✅ PreToolUse 훅 등록 완료: {settings_file}")


# ── CLI
def main():
    parser = argparse.ArgumentParser(description="BRIDGE Backup System v3.0")
    sub = parser.add_subparsers(dest="cmd")

    # backup
    p_bak = sub.add_parser("backup", help="수동 백업")
    p_bak.add_argument("task", help="작업명")
    p_bak.add_argument("--type", default="manual")

    # pre-hook (Claude Code 자동 호출)
    p_pre = sub.add_parser("pre-hook", help="훅 자동 백업")
    p_pre.add_argument("tool_name", nargs="?", default="unknown")

    # list
    p_ls = sub.add_parser("list", help="백업 목록")
    p_ls.add_argument("-n", type=int, default=10)

    # rollback
    p_rb = sub.add_parser("rollback", help="롤백")
    p_rb.add_argument("snapshot")
    p_rb.add_argument("--dry-run", action="store_true")

    # register
    sub.add_parser("register", help="Claude Code 훅 등록")

    # status
    sub.add_parser("status", help="백업 상태")

    args = parser.parse_args()

    if args.cmd == "backup":
        meta = create_backup(args.task, args.type)
        print(f"\n✅ 백업 완료")
        print(f"   경로  : {Path(meta['snapshot_dir']).name}")
        print(f"   파일  : {meta['total_files']}개 / {meta['total_size']//1024}KB")
        print(f"   DB    : {meta['db_hash']}")
        print(f"   Git   : {meta['git_head']} ({meta['git_status']})")
        if meta["errors"]:
            print(f"   ⚠️ 오류: {len(meta['errors'])}건")

    elif args.cmd == "pre-hook":
        # Claude Code가 파일 수정 전 자동 호출
        tool = args.tool_name
        # write/edit 계열 도구만 백업 트리거
        WRITE_TOOLS = {"str_replace_based_edit_tool", "create_file", "write_file",
                       "bash", "computer_use"}
        if any(t in tool.lower() for t in ["edit", "write", "create", "bash", "computer"]):
            meta = create_backup(f"pre_{tool}", task_type="auto-pre-tool")
            print(f"[backup] ✅ pre-hook: {Path(meta['snapshot_dir']).name}")
        else:
            print(f"[backup] skip: {tool}")

    elif args.cmd == "list":
        list_backups(args.n)

    elif args.cmd == "rollback":
        rollback(args.snapshot, args.dry_run)

    elif args.cmd == "register":
        register_hook()

    elif args.cmd == "status":
        state = load_state()
        print(f"\n{'='*60}")
        print(f"BRIDGE 백업 상태")
        print(f"{'='*60}")
        print(f"  마지막 백업 : {state.get('last_backup', '없음')}")
        print(f"  총 백업 수  : {state.get('total_count', 0)}개")
        dirs = list(BACKUP.iterdir()) if BACKUP.exists() else []
        total_size = sum(
            f.stat().st_size for d in dirs if d.is_dir()
            for f in d.rglob("*") if f.is_file()
        )
        print(f"  디스크 사용 : {total_size // (1024*1024)}MB")
        print(f"  로그 파일   : {LOG_FILE}")
        print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
