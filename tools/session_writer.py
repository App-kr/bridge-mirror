import sys, json, os, re
from datetime import datetime

BASE  = r"Q:\Claudework\bridge base"
STATE = os.path.join(BASE, ".claude", "work_state.md")
SLOG  = os.path.join(BASE, ".claude", "session_log.md")

def safe_read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

def safe_write(path, content):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass

def update_state(cmd, failed):
    ts     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "실패" if failed else "완료"
    content = safe_read(STATE) or "# BRIDGE 작업 상태\n"
    marker  = "## 세션 종료 전 마지막 상태"
    entry   = f"{marker}\n시각: {ts}\n명령: {cmd[:200]}\n결과: {status}\n"
    if marker in content:
        content = content[:content.index(marker)] + entry
    else:
        content += "\n" + entry
    safe_write(STATE, content)

def trim_session_log(content, keep=5):
    header_end = content.find("---")
    if header_end == -1:
        return content
    header = content[:header_end]
    blocks = re.findall(r"---.*?(?=---|$)", content[header_end:], re.DOTALL)
    blocks = [b.strip() for b in blocks if b.strip() and b.strip() != "---"]
    kept   = blocks[:keep]
    return header + "\n".join("---\n" + b + "\n---" for b in kept) + "\n"

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tn  = data.get("tool_name", "").lower()
    ti  = data.get("tool_input", {})
    out = str(data.get("tool_response", ""))
    cmd = ti.get("command", ti.get("path", ""))
    if tn != "bash" or not cmd:
        sys.exit(0)
    failed = "exit code 1" in out.lower() or "error:" in out.lower()
    update_state(cmd, failed)
    log_content = safe_read(SLOG)
    if log_content:
        safe_write(SLOG, trim_session_log(log_content, 5))
    sys.exit(0)

main()
