"""
Secret Scanner — Layer 4 (PreToolUse hook)
Write/Edit 작업 전 시크릿 패턴 탐지 후 차단.
stdin: Claude hook JSON
exit 0: 허용 / stdout JSON block: 차단
"""
import json, sys, re

PATTERNS = [
    (r'sk-[A-Za-z0-9]{40,}',                        'Anthropic/OpenAI API key'),
    (r'AIza[0-9A-Za-z_\-]{35}',                      'Google API key'),
    (r'ghp_[A-Za-z0-9]{36}',                          'GitHub PAT'),
    (r'gho_[A-Za-z0-9]{36}',                          'GitHub OAuth token'),
    (r'AKIA[0-9A-Z]{16}',                             'AWS Access Key'),
    (r'[A-Za-z0-9+/]{40,}={0,2}.*(?:secret|key|token|password)', 'Possible secret value'),
    (r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']{8,}', 'Hardcoded password'),
    (r'-----BEGIN\s+(?:RSA|EC|OPENSSH)\s+PRIVATE KEY', 'Private key'),
    (r'(?:BRIDGE_FIELD_KEY|JWT_SECRET|ADMIN_KEY)\s*=\s*[A-Za-z0-9+/=_-]{20,}', 'Bridge secret'),
]

ALLOW_PATHS = [
    '.env.example', '.gitignore', 'incident_response.md',
    'SECURITY_POLICY.md', '.gitleaks.toml', 'secret_scanner.py',
]

def scan_text(text: str) -> list:
    findings = []
    for pattern, label in PATTERNS:
        matches = re.findall(pattern, text, re.I)
        if matches:
            findings.append(f"{label} ({len(matches)} match)")
    return findings

def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {})

    content = ""
    path = ""

    if tool in ("Write", "Edit", "NotebookEdit"):
        content = inp.get("content", "") + inp.get("new_string", "")
        path = inp.get("file_path", "")
    elif tool == "Bash":
        content = inp.get("command", "")
    else:
        sys.exit(0)

    # 허용 경로 제외
    if any(a in path for a in ALLOW_PATHS):
        sys.exit(0)

    findings = scan_text(content)
    if findings:
        out = {
            "decision": "block",
            "reason": "secret_scanner: possible secret detected — " + ", ".join(findings) +
                      " | If intentional, use --no-verify equivalent or check the pattern."
        }
        print(json.dumps(out))
        sys.exit(0)

    sys.exit(0)

if __name__ == "__main__":
    main()
