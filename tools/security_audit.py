"""
npm Supply Chain Security Audit — Layer 2
Runs npm audit, checks for high/critical vulnerabilities.
Usage: python security_audit.py [--path <dir>]
"""
import json, subprocess, sys, os
from pathlib import Path
from datetime import datetime

def run_audit(project_path: Path) -> dict:
    result = subprocess.run(
        ["npm", "audit", "--json"],
        cwd=str(project_path),
        capture_output=True, text=True
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": result.stderr or result.stdout}

def check_postinstall(project_path: Path) -> list:
    """package.json 및 node_modules의 postinstall 스크립트 탐지"""
    findings = []
    pkg = project_path / "package.json"
    if pkg.exists():
        data = json.loads(pkg.read_text(encoding="utf-8"))
        scripts = data.get("scripts", {})
        for name, cmd in scripts.items():
            if any(x in cmd for x in ["curl", "wget", "eval", "exec", "base64"]):
                findings.append(f"SUSPICIOUS script '{name}': {cmd}")

    # node_modules 직접 검사 (설치된 패키지들)
    nm = project_path / "node_modules"
    if nm.exists():
        for pkg_dir in nm.iterdir():
            if not pkg_dir.is_dir():
                continue
            pkg_json = pkg_dir / "package.json"
            if not pkg_json.exists():
                continue
            try:
                d = json.loads(pkg_json.read_text(encoding="utf-8", errors="ignore"))
                for hook in ["preinstall", "postinstall", "install", "prepack"]:
                    cmd = d.get("scripts", {}).get(hook, "")
                    if cmd and any(x in cmd for x in ["curl", "wget", "eval", "exec", "base64", "http"]):
                        findings.append(f"PACKAGE {pkg_dir.name} {hook}: {cmd[:120]}")
            except Exception:
                pass
    return findings

def main():
    base = Path(r"Q:\Claudework\bridge base\web_frontend")
    if "--path" in sys.argv:
        base = Path(sys.argv[sys.argv.index("--path") + 1])

    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] npm security audit: {base}")

    # 1. npm audit
    audit = run_audit(base)
    if "error" in audit:
        print(f"  AUDIT ERROR: {audit['error'][:200]}")
    else:
        vulns = audit.get("metadata", {}).get("vulnerabilities", {})
        critical = vulns.get("critical", 0)
        high = vulns.get("high", 0)
        moderate = vulns.get("moderate", 0)
        print(f"  Vulnerabilities — critical:{critical} high:{high} moderate:{moderate}")
        if critical > 0 or high > 0:
            print(f"  [ALERT] Critical/High vulnerabilities found! Run: npm audit fix")

    # 2. postinstall 스크립트 점검
    findings = check_postinstall(base)
    if findings:
        print(f"  [ALERT] Suspicious scripts found ({len(findings)}):")
        for f in findings[:10]:
            print(f"    {f}")
    else:
        print("  Postinstall scripts: clean")

    # 3. .npmrc ignore-scripts 확인
    npmrc = base / ".npmrc"
    if npmrc.exists() and "ignore-scripts=true" in npmrc.read_text():
        print("  .npmrc ignore-scripts=true: OK")
    else:
        print("  [WARN] .npmrc ignore-scripts=true missing!")

    return 1 if (critical > 0 or findings) else 0

if __name__ == "__main__":
    sys.exit(main())
