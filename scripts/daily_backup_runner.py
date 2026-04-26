"""
daily_backup_runner.py — 일일 무료·안전 백업 자동 실행기

기존 도구 3개를 순차 호출 (잘 되는 것을 건드리지 않고 wrapper만 추가):
  1. tools/db_backup_enc.py encrypt    — master.db → master.db.enc (AES-256-GCM)
  2. tools/render_db_backup.py         — Render /data/master.db → SQL dump
  3. tools/bridge_backup.py backup     — 전체 프로젝트 스냅샷 (선택, type=daily)

각 단계 결과 코드 0/1 합산 → 모두 0이어야 success.
실패 시 텔레그램 알림(있으면).

사용법:
  "Q:/Phtyon 3/python.exe" -X utf8 scripts/daily_backup_runner.py
  "Q:/Phtyon 3/python.exe" -X utf8 scripts/daily_backup_runner.py --skip-render
  "Q:/Phtyon 3/python.exe" -X utf8 scripts/daily_backup_runner.py --quick   # bridge_backup 생략

Task Scheduler 등록은 scripts/register_daily_backup.bat (관리자 권한 1회 실행).
"""
from __future__ import annotations

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PYTHON = os.environ.get("BRIDGE_PYTHON", r"Q:\Phtyon 3\python.exe")
LOG_DIR = BASE / "logs" / "daily_backup"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG = LOG_DIR / f"{datetime.now().strftime('%Y%m%d')}.log"


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line)
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _ensure_field_key() -> bool:
    """BX 크리덴셜 → 환경변수 로드. db_backup_enc.py 가 interactive prompt 안 걸리도록."""
    if os.environ.get("BRIDGE_FIELD_KEY"):
        return True
    try:
        sys.path.insert(0, str(BASE / "tools"))
        import bx  # type: ignore
        bx.load_to_env()
    except Exception as e:
        log(f"  ⚠ BX 로드 실패: {e}")
    return bool(os.environ.get("BRIDGE_FIELD_KEY"))


def _ensure_admin_key() -> bool:
    """ADMIN_API_KEY (BX) → BRIDGE_ADMIN_KEY (render_db_backup가 기대하는 이름) 별칭."""
    if os.environ.get("BRIDGE_ADMIN_KEY"):
        return True
    src = os.environ.get("ADMIN_API_KEY") or os.environ.get("BRIDGE_ADMIN_KEY")
    if src:
        os.environ["BRIDGE_ADMIN_KEY"] = src
        return True
    return False


def run(label: str, cmd: list[str], timeout_s: int = 600) -> int:
    log(f"▶ {label}")
    log(f"  cmd: {' '.join(cmd)}")
    try:
        r = subprocess.run(
            cmd,
            cwd=str(BASE),
            timeout=timeout_s,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,  # interactive prompt 차단 (BRIDGE_FIELD_KEY 미설정 시 즉시 실패)
            env=os.environ.copy(),
        )
        if r.stdout:
            for ln in r.stdout.strip().splitlines()[-15:]:
                log(f"  | {ln}")
        if r.returncode != 0 and r.stderr:
            for ln in r.stderr.strip().splitlines()[-10:]:
                log(f"  ! {ln}")
        log(f"  exit={r.returncode}")
        return r.returncode
    except subprocess.TimeoutExpired:
        log(f"  ⏱ timeout {timeout_s}s")
        return 124
    except Exception as e:
        log(f"  ✗ exception: {e}")
        return 1


def notify_failure(label: str, code: int) -> None:
    """tg_notify.py 가 있으면 텔레그램 실패 알림."""
    tg = BASE / "tools" / "tg_notify.py"
    if not tg.exists():
        return
    try:
        subprocess.run(
            [PYTHON, "-X", "utf8", str(tg), f"⚠ daily_backup 실패: {label} (code={code})"],
            cwd=str(BASE),
            timeout=15,
        )
    except Exception:
        pass


def main() -> int:
    args = sys.argv[1:]
    skip_render = "--skip-render" in args
    quick = "--quick" in args

    log("=" * 60)
    log(f"daily_backup_runner 시작 (skip_render={skip_render}, quick={quick})")
    log(f"BASE={BASE}")
    log(f"PYTHON={PYTHON}")

    fails: list[tuple[str, int]] = []
    skipped: list[str] = []

    # 0) BRIDGE_FIELD_KEY 사전 로드 (interactive prompt 방지)
    if not _ensure_field_key():
        log("⚠ BRIDGE_FIELD_KEY 없음 → db_backup_enc 단계 skip")
        skipped.append("db_backup_enc (no key)")
    else:
        # 1) DB 암호화 백업 — master.db.enc
        code = run(
            "db_backup_enc encrypt",
            [PYTHON, "-X", "utf8", str(BASE / "tools" / "db_backup_enc.py"), "encrypt"],
            timeout_s=180,
        )
        if code != 0:
            fails.append(("db_backup_enc", code))

    # 2) Render DB SQL dump (BRIDGE_ADMIN_KEY 필요 — 미설정 시 자체 스킵)
    if not skip_render:
        if not _ensure_admin_key():
            log("⚠ ADMIN_API_KEY 없음 → render_db_backup 단계 skip")
            skipped.append("render_db_backup (no admin key)")
        else:
            code = run(
                "render_db_backup",
                [PYTHON, "-X", "utf8", str(BASE / "tools" / "render_db_backup.py")],
                timeout_s=180,
            )
            if code != 0:
                fails.append(("render_db_backup", code))

    # 3) bridge_backup 전체 스냅샷 (선택)
    if not quick:
        code = run(
            "bridge_backup",
            [
                PYTHON,
                "-X",
                "utf8",
                str(BASE / "tools" / "bridge_backup.py"),
                "backup",
                f"daily_{datetime.now().strftime('%Y%m%d')}",
                "--type",
                "daily",
            ],
            timeout_s=600,
        )
        if code != 0:
            fails.append(("bridge_backup", code))

    # 4) GitHub Releases 클라우드 이중화 (gh CLI repo scope만 필요)
    if os.environ.get("BRIDGE_FIELD_KEY"):
        code = run(
            "github_release_backup",
            [PYTHON, "-X", "utf8", str(BASE / "scripts" / "github_release_backup.py")],
            timeout_s=300,
        )
        if code != 0:
            fails.append(("github_release_backup", code))
    else:
        skipped.append("github_release_backup (no key)")

    log("-" * 60)
    for s in skipped:
        log(f"⏭ skipped: {s}")

    if not fails:
        log("✅ 전체 성공" + (f" (skipped {len(skipped)})" if skipped else ""))
        return 0

    for name, c in fails:
        log(f"❌ 실패: {name} (code={c})")
        notify_failure(name, c)
    return 1


if __name__ == "__main__":
    sys.exit(main())
