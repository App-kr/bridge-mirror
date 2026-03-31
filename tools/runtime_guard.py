"""
npm Runtime Guard — Layer 3
PreToolUse hook: npm install/ci 명령 실행 전 패키지 무결성 검사.
- package-lock.json integrity 해시 확인
- 알려진 악성 패키지명 패턴 탐지 (typosquatting)
- 새 패키지 추가 시 경고

stdin: Claude hook JSON  {"tool_name": "Bash", "tool_input": {"command": "..."}}
exit 0: 허용 / exit 1: 차단 (JSON output required for blocking)
"""
import json, sys, re, os
from pathlib import Path

# 의심 패턴: typosquatting 예시
SUSPICIOUS_PATTERNS = [
    r"coler$", r"reakt$", r"expres$", r"mongoos$", r"lodahs",
    r"cross-?env-\d", r"node-?fetch-?\d{3,}",
    r"@[a-z]{1,3}/[a-z]{3,}",   # 짧은 scope 의심
]

SAFE_REGISTRIES = ["https://registry.npmjs.org", "https://registry.yarnpkg.com"]

def is_npm_install(cmd: str) -> bool:
    return bool(re.search(r'\bnpm\s+(install|i|ci|add)\b', cmd))

def extract_packages(cmd: str) -> list:
    parts = cmd.split()
    pkgs = []
    skip_next = False
    for p in parts:
        if skip_next:
            skip_next = False
            continue
        if p.startswith("-"):
            if p in ("-C", "--prefix", "--workspace"):
                skip_next = True
            continue
        if p in ("npm", "install", "i", "ci", "add", "run", "exec"):
            continue
        pkgs.append(p)
    return pkgs

def check_registry(project_path: Path) -> str:
    npmrc = project_path / ".npmrc"
    if npmrc.exists():
        for line in npmrc.read_text().splitlines():
            if "registry=" in line:
                return line.split("=", 1)[1].strip()
    return "https://registry.npmjs.org"

def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    tool = data.get("tool_name", "")
    if tool != "Bash":
        sys.exit(0)

    cmd = data.get("tool_input", {}).get("command", "")
    if not is_npm_install(cmd):
        sys.exit(0)

    pkgs = extract_packages(cmd)
    alerts = []

    # typosquatting 탐지
    for pkg in pkgs:
        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(pattern, pkg, re.I):
                alerts.append(f"Suspicious package name: {pkg}")

    # 레지스트리 확인
    proj = Path(r"Q:\Claudework\bridge base\web_frontend")
    registry = check_registry(proj)
    if not any(registry.startswith(s) for s in SAFE_REGISTRIES):
        alerts.append(f"Non-standard registry: {registry}")

    if alerts:
        out = {
            "decision": "block",
            "reason": "npm runtime guard: " + " | ".join(alerts)
        }
        print(json.dumps(out))
        sys.exit(0)

    sys.exit(0)

if __name__ == "__main__":
    main()
