r"""
auto_security_patch.py v2.0 — 자가 진화형 완전 무인 보안 패치
완전 무료, 외부 유료 서비스 미사용

진화 기능:
  1. 자가 업데이트 — 실행 전 git pull (스크립트 최신화)
  2. Major 버전 격리 테스트 — 새 venv에서 설치 + import 검증
  3. 배포 후 건강 검증 — /health 확인 → 실패 시 자동 revert
  4. 도구 자기 갱신 — bandit/pip-audit 자동 업그레이드
  5. 실패 학습 — .patch_state.json 에 시도 이력 저장

사용법:
  python tools/auto_security_patch.py check         # DRY RUN (변경 없음)
  python tools/auto_security_patch.py apply         # 실제 패치 + 커밋 + 배포 + 검증
  python tools/auto_security_patch.py register      # 매주 월 04:00 자동 실행 등록
  python tools/auto_security_patch.py self-update   # 도구 자체만 업데이트

전체 파이프라인 (apply):
  [0] git pull (자가 업데이트)
  [1] 도구 버전 체크 (bandit/pip-audit)
  [2] pip-audit JSON 스캔
  [3] 취약점 분류: patch/minor/major
  [4] patch+minor: 자동 적용
  [5] major: 격리 venv에서 설치+import 테스트 → 통과 시 적용
  [6] pip --dry-run 충돌 검증
  [7] git commit + push
  [8] Render API 배포 트리거
  [9] 최대 10분간 /health 폴링 → live 확인
  [10] 핵심 엔드포인트 smoke test
  [11] 실패 시: git revert + Render 롤백 배포 + 긴급 알림
  [12] 성공 시: 텔레그램 성공 알림 + .patch_state 업데이트
"""
from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REQS = BASE_DIR / "requirements.txt"
STATE_FILE = BASE_DIR / ".patch_state.json"
LOG_FILE = BASE_DIR / "logs" / "auto_security_patch.log"
LOG_FILE.parent.mkdir(exist_ok=True)

PYTHON_EXE = "Q:/Phtyon 3/python.exe"
PIP_AUDIT = "Q:/Phtyon 3/Scripts/pip-audit.exe"
RENDER_SID = "srv-d6imvn1aae7s73ck5570"  # BRIDGE 서비스
HEALTH_URL = "https://bridge-n7hk.onrender.com/health"
SMOKE_URLS = [
    "https://bridge-n7hk.onrender.com/health",
    "https://bridge-n7hk.onrender.com/api/public/talents?limit=1",
]

sys.path.insert(0, str(BASE_DIR))


# ── 로깅 ───────────────────────────────────────────────────────────────────
def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ── 상태 파일 (학습용) ──────────────────────────────────────────────────────
def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"runs": [], "failed_upgrades": {}, "successful_upgrades": {}}


def _save_state(state: dict):
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        _log(f"state 저장 실패: {e}")


# ── 텔레그램 ────────────────────────────────────────────────────────────────
def _notify(msg: str):
    try:
        from tools.tg_notify import send_telegram  # type: ignore
        send_telegram(msg)
    except Exception as e:
        _log(f"텔레그램 실패: {e}")


# ── 자가 업데이트 (git pull) ───────────────────────────────────────────────
def self_update():
    """실행 전 git pull — 스크립트 자체가 최신 버전으로 진화"""
    _log("[0] 자가 업데이트 — git pull")
    try:
        r = subprocess.run(
            ["git", "pull", "--ff-only", "origin", "main"],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0:
            _log(f"  git pull 실패 (계속 진행): {r.stderr[:200]}")
            return False
        if "Already up to date" in r.stdout or "Already up-to-date" in r.stdout:
            _log("  이미 최신 버전")
        else:
            _log(f"  업데이트됨:\n{r.stdout[:300]}")
            # 스크립트 자체가 업데이트됐으면 재실행
            if "auto_security_patch.py" in r.stdout:
                _log("  자신이 업데이트됨 — 새 버전으로 재실행")
                os.execv(sys.executable, [sys.executable, __file__] + sys.argv[1:])
        return True
    except Exception as e:
        _log(f"  git pull 예외: {e}")
        return False


# ── 도구 자기 갱신 ─────────────────────────────────────────────────────────
def upgrade_tools():
    """bandit, pip-audit 자체를 최신 버전으로 업그레이드"""
    _log("[1] 도구 자기 갱신 — bandit, pip-audit")
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    try:
        r = subprocess.run(
            [PYTHON_EXE, "-m", "pip", "install", "--upgrade",
             "bandit", "pip-audit", "pre-commit"],
            capture_output=True, text=True, timeout=180, env=env,
        )
        if r.returncode != 0:
            _log(f"  업그레이드 실패: {r.stderr[:200]}")
        else:
            _log("  도구 최신화 완료")
    except Exception as e:
        _log(f"  예외: {e}")


# ── pip-audit 스캔 ─────────────────────────────────────────────────────────
def pip_audit_scan() -> list[dict]:
    """pip-audit 실행 → 취약점 JSON"""
    _log("[2] pip-audit CVE 스캔")
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        r = subprocess.run(
            [PIP_AUDIT, "-r", str(REQS), "--format", "json"],
            capture_output=True, text=True, timeout=180, env=env,
        )
        data = json.loads(r.stdout)
        deps = data.get("dependencies", [])
        return deps
    except Exception as e:
        _log(f"  pip-audit 실패: {e}")
        return []


def classify_vulns(deps: list[dict]) -> dict:
    """취약점 분류: patch / minor / major"""
    result = {"patch": [], "minor": [], "major": []}
    for d in deps:
        pkg = d.get("name", "")
        curr = d.get("version", "")
        for v in d.get("vulns", []):
            fixes = v.get("fix_versions", [])
            if not fixes:
                continue
            target = sorted(fixes, key=lambda x: tuple(
                int(p) if p.isdigit() else 0 for p in x.split(".")[:3]
            ))[0]
            entry = {
                "pkg": pkg, "curr": curr, "fix": target,
                "cve": v.get("id", ""),
                "desc": v.get("description", "")[:100],
            }
            tier = _version_tier(curr, target)
            result[tier].append(entry)
    return result


def _version_tier(curr: str, target: str) -> str:
    try:
        c = [int(p) for p in curr.split(".")[:3]]
        t = [int(p) for p in target.split(".")[:3]]
        while len(c) < 3: c.append(0)
        while len(t) < 3: t.append(0)
        if c[0] != t[0]:
            return "major"
        if c[1] != t[1]:
            return "minor"
        return "patch"
    except Exception:
        return "major"  # 파싱 실패 = 보수적으로 major로 취급


# ── Major 버전 격리 테스트 ─────────────────────────────────────────────────
def test_major_upgrade(pkg: str, target: str) -> bool:
    """격리 venv에 새 버전 설치 + import 테스트"""
    _log(f"  [격리 테스트] {pkg}=={target}")
    with tempfile.TemporaryDirectory() as td:
        venv_dir = Path(td) / "venv"
        try:
            r1 = subprocess.run(
                [PYTHON_EXE, "-m", "venv", str(venv_dir)],
                capture_output=True, text=True, timeout=60,
            )
            if r1.returncode != 0:
                _log(f"    venv 생성 실패: {r1.stderr[:100]}")
                return False
            venv_py = venv_dir / "Scripts" / "python.exe"
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            r2 = subprocess.run(
                [str(venv_py), "-m", "pip", "install", "--quiet",
                 f"{pkg}=={target}"],
                capture_output=True, text=True, timeout=300, env=env,
            )
            if r2.returncode != 0:
                _log(f"    설치 실패: {r2.stderr[:200]}")
                return False
            # import 테스트
            import_name = pkg.replace("-", "_").split("[")[0]
            # 특수 케이스
            if pkg.lower() == "pillow":
                import_name = "PIL"
            elif pkg.lower() == "pyjwt":
                import_name = "jwt"
            r3 = subprocess.run(
                [str(venv_py), "-c", f"import {import_name}; print('OK')"],
                capture_output=True, text=True, timeout=30,
            )
            if r3.returncode != 0:
                _log(f"    import 실패: {r3.stderr[:200]}")
                return False
            _log(f"    [PASS] 설치 + import 성공")
            return True
        except Exception as e:
            _log(f"    예외: {e}")
            return False


# ── requirements.txt 수정 ──────────────────────────────────────────────────
def update_requirements(approved: list[dict]) -> list[dict]:
    """requirements.txt 수정, 실제 적용된 목록 반환"""
    if not approved:
        return []
    shutil.copy2(REQS, REQS.with_suffix(".txt.bak"))
    text = REQS.read_text(encoding="utf-8")
    lines = text.splitlines()
    new_lines = []
    applied = []
    approved_map = {v["pkg"].lower(): v for v in approved}

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        m = re.match(r"^([A-Za-z0-9_\-\[\]]+)\s*([=<>!~].*)?$", stripped)
        if not m:
            new_lines.append(line)
            continue
        pkg_name = m.group(1).split("[")[0].lower()
        match = approved_map.get(pkg_name)
        if not match:
            new_lines.append(line)
            continue
        # 기존 주석 보존
        comment = ""
        if "#" in line:
            comment = "  " + line[line.index("#"):]
        new_line = f"{m.group(1)}=={match['fix']}{comment}"
        new_lines.append(new_line)
        applied.append(match)

    REQS.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return applied


# ── pip 충돌 검증 ──────────────────────────────────────────────────────────
def verify_dependencies() -> bool:
    _log("[6] 의존성 충돌 검증 (pip --dry-run)")
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    r = subprocess.run(
        [PYTHON_EXE, "-m", "pip", "install", "--dry-run", "-r", str(REQS)],
        capture_output=True, text=True, timeout=300, env=env,
    )
    if r.returncode != 0:
        _log(f"  충돌:\n{r.stderr[:400]}")
        return False
    _log("  OK")
    return True


# ── Git commit + push ──────────────────────────────────────────────────────
def git_commit_push(applied: list[dict]) -> tuple[bool, str]:
    _log("[7] git commit + push")
    try:
        r = subprocess.run(["git", "diff", "--quiet", str(REQS)],
                           cwd=BASE_DIR, capture_output=True)
        if r.returncode == 0:
            return True, "변경 없음"
        subject = f"security(deps): auto-patch {len(applied)} CVE"
        body_lines = [f"- {a['pkg']} {a['curr']} → {a['fix']} ({a['cve']})"
                      for a in applied[:15]]
        full_msg = subject + "\n\n" + "\n".join(body_lines) + "\n\nauto_security_patch.py v2.0"
        subprocess.run(["git", "add", "requirements.txt"], cwd=BASE_DIR, check=True)
        subprocess.run(["git", "commit", "-m", full_msg], cwd=BASE_DIR, check=True)
        r2 = subprocess.run(["git", "push", "origin", "main"],
                            cwd=BASE_DIR, capture_output=True, text=True, timeout=120)
        if r2.returncode != 0:
            return False, f"push 실패: {r2.stderr[:300]}"
        # 방금 만든 커밋 해시 반환
        h = subprocess.run(["git", "rev-parse", "HEAD"], cwd=BASE_DIR,
                           capture_output=True, text=True).stdout.strip()
        return True, h
    except Exception as e:
        return False, f"git 예외: {e}"


# ── Render 배포 ────────────────────────────────────────────────────────────
def trigger_render_deploy() -> tuple[bool, str]:
    _log("[8] Render 배포 트리거")
    import urllib.request
    try:
        from tools.bx import _read  # type: ignore
        token = _read("RENDER_API_KEY")
        if not token:
            return False, "RENDER_API_KEY 없음"
        req = urllib.request.Request(
            f"https://api.render.com/v1/services/{RENDER_SID}/deploys",
            data=b'{"clearCache":"do_not_clear"}',
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read())
        return True, res.get("id", "")
    except Exception as e:
        return False, f"배포 실패: {e}"


def wait_for_deploy(deploy_id: str, timeout_sec: int = 600) -> bool:
    """배포 완료까지 대기 (최대 10분)"""
    _log(f"[9] 배포 완료 대기 (최대 {timeout_sec}초)")
    import urllib.request
    from tools.bx import _read  # type: ignore
    token = _read("RENDER_API_KEY")
    start = time.time()
    while time.time() - start < timeout_sec:
        time.sleep(15)
        try:
            req = urllib.request.Request(
                f"https://api.render.com/v1/services/{RENDER_SID}/deploys/{deploy_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                d = json.loads(r.read())
            status = d.get("status", "")
            _log(f"  배포 상태: {status}")
            if status == "live":
                return True
            if status in ("build_failed", "update_failed", "canceled", "deactivated"):
                _log(f"  배포 실패: {status}")
                return False
        except Exception as e:
            _log(f"  폴링 오류: {e}")
    _log("  타임아웃")
    return False


def smoke_test() -> bool:
    """핵심 엔드포인트 건강 검증"""
    _log("[10] smoke test")
    import urllib.request
    for url in SMOKE_URLS:
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                body = r.read(2048)
                if r.status != 200:
                    _log(f"  FAIL {url} status={r.status}")
                    return False
                if url.endswith("/health") and b"ok" not in body.lower():
                    _log(f"  FAIL {url} body suspect")
                    return False
        except Exception as e:
            _log(f"  FAIL {url}: {e}")
            return False
    _log("  모든 엔드포인트 200 OK")
    return True


def auto_rollback(commit_hash: str):
    """배포 실패 시 commit revert + 재배포"""
    _log(f"[11] 자동 롤백 시작 — commit {commit_hash[:8]}")
    try:
        subprocess.run(["git", "revert", "--no-edit", commit_hash],
                       cwd=BASE_DIR, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"],
                       cwd=BASE_DIR, check=True, capture_output=True, timeout=120)
        ok, did = trigger_render_deploy()
        _log(f"  롤백 배포: {did if ok else '실패'}")
        _notify(f"🚨 BRIDGE 자동 패치 실패 → 자동 롤백됨\n"
                f"revert: {commit_hash[:8]}\n"
                f"롤백 배포: {did if ok else '실패'}\n"
                f"수동 검토 필요")
    except Exception as e:
        _log(f"  롤백 실패: {e}")
        _notify(f"🚨🚨 BRIDGE 긴급: 자동 롤백 실패! 수동 개입 필요\n{e}")


# ── 메인 로직 ──────────────────────────────────────────────────────────────
def cmd_check():
    self_update()
    upgrade_tools()
    deps = pip_audit_scan()
    vulns = classify_vulns(deps)
    total = sum(len(v) for v in vulns.values())
    if total == 0:
        _log("CLEAN — 취약점 없음")
        return
    _log(f"DRY RUN — 취약점 {total}건")
    for tier in ("patch", "minor", "major"):
        for v in vulns[tier]:
            _log(f"  [{tier}] {v['pkg']} {v['curr']} → {v['fix']} ({v['cve']})")


def cmd_apply():
    state = _load_state()
    run_record = {
        "started": datetime.now().isoformat(),
        "applied": [], "failed": [], "skipped": [],
    }

    self_update()
    upgrade_tools()
    deps = pip_audit_scan()
    vulns = classify_vulns(deps)
    total = sum(len(v) for v in vulns.values())

    if total == 0:
        _log("CLEAN — 취약점 없음, 종료")
        run_record["result"] = "clean"
        state["runs"].append(run_record)
        _save_state(state)
        return

    _log(f"[3] 취약점 분류: patch={len(vulns['patch'])} "
         f"minor={len(vulns['minor'])} major={len(vulns['major'])}")

    # patch + minor = 자동 적용 대상
    approved = list(vulns["patch"]) + list(vulns["minor"])

    # major = 격리 테스트 후 통과한 것만 승인
    _log(f"[5] major 격리 테스트 ({len(vulns['major'])}건)")
    for v in vulns["major"]:
        key = f"{v['pkg']}=={v['fix']}"
        # 이전 실패 이력 체크 (3회 이상 실패했으면 skip)
        failed = state.get("failed_upgrades", {}).get(key, 0)
        if failed >= 3:
            _log(f"  [SKIP] {key} — 과거 {failed}회 실패")
            run_record["skipped"].append({**v, "reason": f"{failed}회 실패 이력"})
            continue
        if test_major_upgrade(v["pkg"], v["fix"]):
            approved.append(v)
            state.setdefault("successful_upgrades", {})[key] = \
                state.get("successful_upgrades", {}).get(key, 0) + 1
        else:
            state.setdefault("failed_upgrades", {})[key] = failed + 1
            run_record["failed"].append(v)

    if not approved:
        _log("적용 대상 없음")
        _notify(f"⚠️ BRIDGE: {total}건 취약점 발견, 자동 적용 가능 0건 — 수동 검토 필요")
        run_record["result"] = "no_safe_patch"
        state["runs"].append(run_record)
        _save_state(state)
        return

    applied = update_requirements(approved)
    _log(f"[4] requirements.txt 수정: {len(applied)}건")
    run_record["applied"] = applied

    if not verify_dependencies():
        bak = REQS.with_suffix(".txt.bak")
        if bak.exists():
            shutil.copy2(bak, REQS)
        _notify(f"🚨 BRIDGE auto-patch: 의존성 충돌 — requirements.txt 롤백됨")
        run_record["result"] = "dep_conflict"
        state["runs"].append(run_record)
        _save_state(state)
        return

    ok, hash_or_err = git_commit_push(applied)
    if not ok:
        _notify(f"🚨 BRIDGE: git 실패 — {hash_or_err}")
        run_record["result"] = "git_fail"
        state["runs"].append(run_record)
        _save_state(state)
        return
    commit_hash = hash_or_err
    _log(f"  커밋: {commit_hash[:8]}")

    ok2, deploy_id = trigger_render_deploy()
    if not ok2:
        _notify(f"⚠️ BRIDGE: Render 배포 트리거 실패 — {deploy_id}")
        run_record["result"] = "deploy_trigger_fail"
        state["runs"].append(run_record)
        _save_state(state)
        return

    if not wait_for_deploy(deploy_id):
        auto_rollback(commit_hash)
        run_record["result"] = "deploy_fail_rolled_back"
        state["runs"].append(run_record)
        _save_state(state)
        return

    # smoke test — 실패 시 롤백
    if not smoke_test():
        _log("smoke test 실패 — 자동 롤백")
        auto_rollback(commit_hash)
        run_record["result"] = "smoke_fail_rolled_back"
        state["runs"].append(run_record)
        _save_state(state)
        return

    # 성공
    pkg_list = ", ".join(f"{a['pkg']}→{a['fix']}" for a in applied[:5])
    more = f" 외 {len(applied)-5}건" if len(applied) > 5 else ""
    _notify(
        f"✅ BRIDGE 자동 보안 패치 성공\n"
        f"{len(applied)}건 CVE 수정: {pkg_list}{more}\n"
        f"commit: {commit_hash[:8]}\n"
        f"deploy: live + smoke test pass"
    )
    run_record["result"] = "success"
    run_record["commit"] = commit_hash
    state["runs"].append(run_record)
    # 최근 50회만 보관
    state["runs"] = state["runs"][-50:]
    _save_state(state)
    _log("[12] 전체 파이프라인 성공")


def cmd_register():
    python = sys.executable
    script = str(Path(__file__).resolve())
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
        _log("Windows 스케줄러 등록: 매주 월 04:00")
    else:
        try:
            err = r.stderr.decode("cp949", errors="ignore")
        except Exception:
            err = str(r.stderr)
        _log(f"등록 실패: {err[:200]}")


def cmd_self_update():
    self_update()
    upgrade_tools()


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
    elif cmd == "self-update":
        cmd_self_update()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
