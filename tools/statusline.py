#!/usr/bin/env python3
"""
BRIDGE Global StatusLine v1.1
Q:\Claudework\bridge base\tools\statusline.py
"""
import subprocess, json, re, sys
from pathlib import Path

def get_ccusage():
    try:
        r = subprocess.run(
            ["npx", "ccusage", "statusline", "--offline"],
            capture_output=True, text=True, timeout=4
        )
        return r.stdout.strip()
    except Exception:
        return ""

def parse_ccusage(line: str):
    model, ctx_pct, ctx_num = "", "", ""
    for part in line.split("|"):
        p = part.strip()
        if any(x in p for x in ["Opus","Sonnet","Haiku"]):
            model = re.sub(r'[🤖💰🔥🧠]','', p).strip()
        if "%" in p and ("🧠" in p or "," in p):
            ctx_pct = p
            m = re.search(r'\((\d+)%\)', p)
            if m:
                ctx_num = int(m.group(1))
    return model, ctx_pct, ctx_num

def recommend(pct, model: str) -> str:
    if not isinstance(pct, int):
        return ""
    # Opus 쓰는데 40% 미만 → Sonnet으로 비용 절감 가능
    if pct < 40 and "Opus" in model:
        return "💡Sonnet추천"
    # 40~70%: 정상
    if pct < 70:
        return ""
    # 70~85%: compact 권고
    if pct < 85:
        return "⚠️/compact"
    # 85%+: 새 세션
    return "🚨새세션"

def get_task() -> str:
    ws = Path(r"Q:\Claudework\bridge base\.claude\WORKSTATE.json")
    if not ws.exists():
        return ""
    try:
        data = json.loads(ws.read_text(encoding="utf-8"))
        data.pop("_sig", None)
        wip = [t for t in data.get("tasks", []) if t.get("status") == "in_progress"]
        if wip:
            t = wip[0]
            return f"{t['id']} {t.get('title','')[:20]}"
    except Exception:
        pass
    return ""

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raw     = get_ccusage()
    model, ctx_pct, ctx_num = parse_ccusage(raw)
    rec     = recommend(ctx_num, model)
    task    = get_task()

    parts = []
    parts.append(f"🤖 {model or 'Opus 4.6'}")
    if ctx_pct:
        parts.append(f"🧠 {ctx_pct}")
    if rec:
        parts.append(rec)
    parts.append(f"📋 {task}" if task else "📋 대기중")

    print(" | ".join(parts))

if __name__ == "__main__":
    main()
