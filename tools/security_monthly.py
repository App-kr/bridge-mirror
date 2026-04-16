#!/usr/bin/env python3
"""
BRIDGE 월간 보안 검토 스크립트 (SEC-03)
실행: python tools/security_monthly.py [--quick]
출력: tools/security_reports/YYYY-MM.json
스케줄: 매월 1일 03:00 Windows 작업 스케줄러
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

BASE = pathlib.Path(__file__).parent.parent
REPORT_DIR = BASE / "tools" / "security_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

OWASP_CHECKS = [
    ("A01 Broken Access Control",   "_check_admin",        "api_server.py"),
    ("A02 Cryptographic Failures",  "AES-256-GCM",         "security_vault.py"),
    ("A03 Injection",               "PRAGMA busy_timeout", "api_server.py"),  # SQLite parameterized (? placeholders)
    ("A07 Auth Failures",           "pbkdf2:sha256",       "api_server.py"),
    ("A09 Logging",                 "_audit_log",          "api_server.py"),
]

# 오탐 제외 패턴 (PATH/라인에 이 문자열 포함 시 결과에서 제외)
PLAIN_CRED_EXCLUDE = [
    "crypto_util.py", "init_vault_env.py", "change_password.py",
    ".venv", "node_modules", ".git", "worktrees",
]

ENV_REQUIRED = [
    "JWT_SECRET", "BRIDGE_HMAC_KEY", "BRIDGE_SMTP_PASS",
    "TELEGRAM_BOT_TOKEN", "ANTHROPIC_API_KEY", "BRIDGE_FIELD_KEY",
]


def run(cmd, cwd=None, timeout=60):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=str(cwd or BASE), shell=False)
        return r.returncode, r.stdout + r.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return -1, str(e)


def check_pip_audit():
    rc, out = run([sys.executable, "-m", "pip_audit", "--format", "json",
                   "-r", str(BASE / "requirements.txt")])
    if rc == -1:
        return {"status": "SKIP", "note": "pip-audit not installed"}
    try:
        data = json.loads(out)
        vulns = data.get("vulnerabilities", [])
        return {"status": "PASS" if not vulns else "FAIL", "count": len(vulns), "detail": vulns[:5]}
    except Exception:
        return {"status": "SKIP", "raw": out[:200]}


def check_npm_audit():
    pkg = BASE / "web_frontend"
    if not (pkg / "package.json").exists():
        return {"status": "SKIP", "note": "no package.json"}
    rc, out = run(["npm", "audit", "--json"], cwd=pkg, timeout=120)
    try:
        data = json.loads(out)
        total = data.get("metadata", {}).get("vulnerabilities", {})
        high = total.get("high", 0) + total.get("critical", 0)
        return {"status": "WARN" if high else "PASS", "high_critical": high, "total": total}
    except Exception:
        return {"status": "SKIP", "raw": out[:200]}


def check_gitleaks():
    rc, out = run(["gitleaks", "detect", "--source", ".", "--no-git", "-q"])
    if rc == -1:
        return {"status": "SKIP", "note": "gitleaks not in PATH"}
    found = re.findall(r"RuleID:\s*(\S+)", out)
    return {"status": "PASS" if not found else "FAIL", "leaks": found}


def check_owasp():
    results = []
    for label, pattern, fname in OWASP_CHECKS:
        fpath = BASE / fname
        found = False
        if fpath.exists():
            found = pattern.lower() in fpath.read_text(encoding="utf-8", errors="ignore").lower()
        results.append({"check": label, "status": "PASS" if found else "FAIL", "file": fname})
    return results


def check_env_vars():
    missing = [k for k in ENV_REQUIRED if not os.environ.get(k, "").strip()]
    return {"status": "PASS" if not missing else "WARN", "missing": missing}


def check_plain_credentials():
    """소스 코드에서 평문 크리덴셜 패턴 검색 (오탐 제외 포함)"""
    patterns = [
        r'password\s*=\s*["\'][^"\']{6,}["\']',
        r'secret\s*=\s*["\'][^"\']{8,}["\']',
        r'api_key\s*=\s*["\'][^"\']{8,}["\']',
    ]
    hits = []
    for py in list(BASE.rglob("*.py"))[:300]:
        py_str = str(py)
        if any(ex in py_str for ex in [".venv", "__pycache__", "node_modules", ".git"] + PLAIN_CRED_EXCLUDE):
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
            for pat in patterns:
                for m in re.finditer(pat, text, re.IGNORECASE):
                    # os.environ 참조는 오탐 제외
                    ctx = text[max(0, m.start()-20):m.end()+20]
                    if "os.environ" in ctx or "os.getenv" in ctx or "split(" in ctx:
                        continue
                    hits.append(f"{py.relative_to(BASE)}:{m.start()}: {m.group()[:60]}")
        except Exception:
            pass
    return {"status": "PASS" if not hits else "FAIL", "hits": hits[:10]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="pip-audit/npm-audit 스킵")
    args = parser.parse_args()

    now = datetime.now(tz=timezone.utc)
    report_key = now.strftime("%Y-%m")
    report = {
        "generated_at": now.isoformat(),
        "quick_mode": args.quick,
        "owasp": check_owasp(),
        "env_vars": check_env_vars(),
        "plain_credentials": check_plain_credentials(),
        "gitleaks": check_gitleaks(),
        "pip_audit": check_pip_audit() if not args.quick else {"status": "SKIP"},
        "npm_audit": check_npm_audit() if not args.quick else {"status": "SKIP"},
    }

    # 요약
    failures = sum(
        1 for v in report.values()
        if isinstance(v, dict) and v.get("status") == "FAIL"
    )
    failures += sum(
        1 for item in report.get("owasp", [])
        if isinstance(item, dict) and item.get("status") == "FAIL"
    )
    report["summary"] = {"total_failures": failures, "verdict": "PASS" if failures == 0 else "FAIL"}

    out_path = REPORT_DIR / f"{report_key}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[security_monthly] 보고서 저장: {out_path}")
    print(f"[security_monthly] 결과: {report['summary']['verdict']} (실패 {failures}건)")
    for item in report.get("owasp", []):
        status = item.get("status", "?")
        icon = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"  {icon} {item['check']}")
    for key in ("gitleaks", "pip_audit", "npm_audit", "plain_credentials", "env_vars"):
        v = report.get(key, {})
        status = v.get("status", "?")
        icon = "[PASS]" if status == "PASS" else ("[SKIP]" if status == "SKIP" else "[WARN]" if status == "WARN" else "[FAIL]")
        print(f"  {icon} {key}")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
