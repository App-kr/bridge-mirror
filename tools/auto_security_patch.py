r"""
auto_security_patch.py — 주기적 자동 보안 패치
완전 무료, 외부 유료 서비스 미사용

동작:
  1. pip-audit로 requirements.txt CVE 스캔
  2. 취약 패키지 자동 업그레이드 (fixed version 있을 때만)
  3. pip install --dry-run으로 의존성 충돌 사전 검증
  4. git diff 확인 후 자동 커밋 + push
  5. Render API로 Manual Deploy 자동 트리거
  6. 텔레그램 결과 알림

사용법:
  python tools/auto_security_patch.py check         # 드라이런 (변경 안 함)
  python tools/auto_security_patch.py apply         # 실제 패치 + 커밋 + 배포
  python tools/auto_security_patch.py register      # 매주 월 04:00 자동 실행 등록

안전장치:
  - Major 버전 업그레이드 차단 (semver patch/minor만 자동)
  - 취약점 없으면 no-op (무한 커밋 방지)
  - pip install --dry-run 실패 시 롤백
  - requirements.txt 백업 .bak 생성
"""
from __future__ import annotations
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REQS = BASE_DIR / "requirements.txt"
LOG_FILE = BASE_DIR / "logs" / "auto_security_patch.log"
LOG_FILE.parent.mkdir(exist_ok=True)

sys.path.insert(0, str(BASE_DIR))


def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _pip_audit_json() -> list[dict]:
    """pip-audit 실행 → 취약점 JSON 목록 반환 (한글 주석 대응)"""
    import os
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(
        ["Q:/Phtyon 3/Scripts/pip-audit.exe", "-r", str(REQS), "--format", "json"],
        capture_output=True, text=True, timeout=180, env=env,
    )
    try:
        data = json.loads(r.stdout)
        return data.get("dependencies", [])
    except Exception as e:
        _log(f"pip-audit 파싱 실패: {e}")
        _log(f"stderr: {r.stderr[:300]}")
        return []


def _find_vulns(deps: list[dict]) -> list[dict]:
    """취약점 있는 패키지만 추출 (fixed version 필수)"""
    vulns = []
    for d in deps:
        pkg = d.get("name", "")
        curr = d.get("version", "")
        for v in d.get("vulns", []):
            fixes = v.get("fix_versions", [])
            if not fixes:
                continue
            # 가장 낮은 fix version (보수적 선택)
            target = sorted(fixes, key=lambda x: [int(p) if p.isdigit() else 0 for p in x.split(".")])[0]
            vulns.append({
                "pkg": pkg,
                "curr": curr,
                "fix": target,
                "cve": v.get("id", ""),
                "desc": v.get("description", "")[:120],
            })
    return vulns


def _is_safe_upgrade(curr: str, target: str) -> bool:
    """major 버전 업그레이드는 거부 (breaking change 방지)"""
    try:
        cm = int(curr.split(".")[0])
        tm = int(target.split(".")[0])
        return tm == cm
    except Exception:
        return False


def _update_requirements(vulns: list[dict]) -> list[dict]:
    """requirements.txt 수정. 실제 적용된 업그레이드 목록 반환."""
    applied = []
    text = REQS.read_text(encoding="utf-8")
    lines = text.splitlines()
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        # pkg==version 또는 pkg>=version,<Y 형태 파싱
        m = re.match(r"^([A-Za-z0-9_\-\[\]]+)\s*([=<>!~].*)?$", stripped)
        if not m:
            new_lines.append(line)
            continue
        pkg_name = m.group(1).split("[")[0].lower()
        # 이 패키지에 대한 취약점이 있는가?
        match = next((v for v in vulns if v["pkg"].lower() == pkg_name), None)
        if not match:
            new_lines.append(line)
            continue
        if not _is_safe_upgrade(match["curr"], match["fix"]):
            _log(f"  SKIP major bump: {match['pkg']} {match['curr']} → {match['fix']}")
            new_lines.append(line)
            continue
        new_line = f"{m.group(1)}=={match['fix']}"
        new_lines.append(new_line)
        applied.append(match)
        _log(f"  PATCH: {match['pkg']} {match['curr']} → {match['fix']} ({match['cve']})")

    if applied:
        # 백업
        shutil.copy2(REQS, REQS.with_suffix(".txt.bak"))
        REQS.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return applied


def _verify_deps() -> bool:
    """pip install --dry-run 으로 의존성 충돌 검증"""
    r = subprocess.run(
        ["Q:/Phtyon 3/python.exe", "-m", "pip", "install", "--dry-run",
         "-r", str(REQS)],
        capture_output=True, text=True, timeout=180,
    )
    if r.returncode != 0:
        _log(f"pip --dry-run 실패:\n{r.stderr[:500]}")
        return False
    return True


def _git_commit_push(applied: list[dict]) -> tuple[bool, str]:
    """변경 커밋 + push"""
    try:
        # 변경 확인
        r = subprocess.run(["git", "diff", "--quiet", str(REQS)],
                           cwd=BASE_DIR, capture_output=True)
        if r.returncode == 0:
            return True, "변경 없음"

        subject = f"security(deps): auto-patch {len(applied)} CVE"
        body_lines = [f"- {a['pkg']} {a['curr']} → {a['fix']} ({a['cve']})" for a in applied[:15]]
        full_msg = subject + "\n\n" + "\n".join(body_lines) + "\n\nauto_security_patch.py"

        subprocess.run(["git", "add", "requirements.txt"], cwd=BASE_DIR, check=True)
        subprocess.run(["git", "commit", "-m", full_msg], cwd=BASE_DIR, check=True)
        r2 = subprocess.run(["git", "push", "origin", "main"],
                            cwd=BASE_DIR, capture_output=True, text=True, timeout=60)
        if r2.returncode != 0:
            return False, f"push 실패: {r2.stderr[:300]}"
        return True, "커밋 + push 완료"
    except subprocess.CalledProcessError as e:
        return False, f"git 실패: {e}"


def _trigger_render_deploy() -> tuple[bool, str]:
    """Render API로 Manual Deploy 트리거"""
    try:
        import urllib.request
        from tools.bx import _read  # type: ignore
        token = _read("RENDER_API_KEY")
        if not token:
            return False, "RENDER_API_KEY 없음 — 배포 스킵"
        SID = "srv-d6imvn1aae7s73ck5570"
        req = urllib.request.Request(
            f"https://api.render.com/v1/services/{SID}/deploys",
            data=b'{"clearCache":"do_not_clear"}',
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            res = json.loads(r.read())
        return True, f"배포 트리거됨 id={res.get('id')}"
    except Exception as e:
        return False, f"배포 실패: {e}"


def _notify(msg: str):
    try:
        from tools.tg_notify import send_telegram  # type: ignore
        send_telegram(msg)
    except Exception as e:
        _log(f"텔레그램 실패: {e}")


def cmd_check():
    _log("자동 보안 패치 — DRY RUN")
    deps = _pip_audit_json()
    vulns = _find_vulns(deps)
    if not vulns:
        _log("취약점 없음 — CLEAN")
        return
    _log(f"취약점 {len(vulns)}건 발견:")
    for v in vulns:
        safe = "OK" if _is_safe_upgrade(v["curr"], v["fix"]) else "SKIP(major)"
        _log(f"  [{safe}] {v['pkg']} {v['curr']} → {v['fix']} ({v['cve']})")


def cmd_apply():
    _log("자동 보안 패치 — APPLY 모드")
    deps = _pip_audit_json()
    vulns = _find_vulns(deps)
    if not vulns:
        _log("취약점 없음 — 종료")
        return

    applied = _update_requirements(vulns)
    if not applied:
        _log("적용 가능한 패치 없음 (전부 major bump)")
        _notify(f"⚠️ BRIDGE: {len(vulns)}개 취약점 발견했으나 전부 major 버전 — 수동 검토 필요")
        return

    _log("의존성 충돌 검증 중...")
    if not _verify_deps():
        # 롤백
        bak = REQS.with_suffix(".txt.bak")
        if bak.exists():
            shutil.copy2(bak, REQS)
            _log("의존성 충돌 — requirements.txt 롤백됨")
        _notify(f"🚨 BRIDGE auto-patch 실패: pip 의존성 충돌 ({len(applied)}건 시도) — 수동 개입 필요")
        return

    ok, msg = _git_commit_push(applied)
    _log(f"git: {msg}")
    if not ok:
        _notify(f"🚨 BRIDGE auto-patch: 커밋/push 실패 — {msg}")
        return

    ok2, msg2 = _trigger_render_deploy()
    _log(f"render: {msg2}")

    pkg_list = ", ".join(f"{a['pkg']}→{a['fix']}" for a in applied[:5])
    _notify(
        f"✅ BRIDGE 자동 보안 패치 완료\n"
        f"{len(applied)}건 CVE 수정: {pkg_list}\n"
        f"git: {msg}\nrender: {msg2}"
    )


def cmd_register():
    python = sys.executable
    script = str(Path(__file__).resolve())
    # 매주 월요일 04:00
    r = subprocess.run([
        "schtasks", "/create",
        "/sc", "weekly", "/d", "MON",
        "/st", "04:00",
        "/tn", "BRIDGE_Auto_Security_Patch",
        "/tr", f'"{python}" "{script}" apply',
        "/rl", "limited",
        "/f",
    ], capture_output=True, creationflags=0x08000000)
    if r.returncode == 0:
        _log("Windows 스케줄러 등록 완료 (매주 월 04:00)")
    else:
        try:
            err_text = r.stderr.decode("cp949", errors="ignore")
        except Exception:
            err_text = str(r.stderr)
        _log(f"등록 실패: {err_text[:200]}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1].lower()
    if cmd == "check":
        cmd_check()
    elif cmd == "apply":
        cmd_apply()
    elif cmd == "register":
        cmd_register()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
