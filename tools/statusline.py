#!/usr/bin/env python3
"""
BRIDGE Global StatusLine v2.1
Q:\Claudework\bridge base\tools\statusline.py

ccusage statusline에 올바른 JSON stdin을 구성하여 파이프하는 방식.
Claude Code settings.json → statusLine.command 로 호출됨.
"""
import subprocess, json, re, sys, os, time
from pathlib import Path

PROJECTS_DIR = Path(os.environ.get("USERPROFILE", r"C:\Users\Scarlett")) / ".claude" / "projects"
NPX = r"Q:\Code\Node\npx.cmd"
# CREATE_NO_WINDOW: 자식 cmd 창 깜빡임 방지 (Windows 전용)
# 2026-04-28 긴급 패치: ccusage 호출 시 cmd 창이 1~5초마다 떠서 사용자 작업 방해
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
# 최근 1시간 이내 수정된 파일만 대상 (오래된 세션 제외)
MAX_AGE_SEC = 3600


def find_session():
    """최근 수정된 JSONL 세션 파일 중 50KB 이상(메인 대화)을 찾는다."""
    if not PROJECTS_DIR.exists():
        return None, None

    now = time.time()
    best_file, best_dir, best_mtime = None, None, 0

    for pdir in PROJECTS_DIR.iterdir():
        if not pdir.is_dir():
            continue
        for jf in pdir.glob("*.jsonl"):
            try:
                st = jf.stat()
            except OSError:
                continue
            # 50KB 미만은 서브에이전트 → 스킵
            if st.st_size < 50_000:
                continue
            # 최근 1시간 이내만
            if (now - st.st_mtime) > MAX_AGE_SEC:
                continue
            if st.st_mtime > best_mtime:
                best_mtime = st.st_mtime
                best_file = jf
                best_dir = pdir

    # 폴백: 시간 제한 없이 가장 최근 파일
    if not best_file:
        for pdir in PROJECTS_DIR.iterdir():
            if not pdir.is_dir():
                continue
            for jf in pdir.glob("*.jsonl"):
                try:
                    st = jf.stat()
                except OSError:
                    continue
                if st.st_size < 50_000:
                    continue
                if st.st_mtime > best_mtime:
                    best_mtime = st.st_mtime
                    best_file = jf
                    best_dir = pdir

    return best_file, best_dir


def read_model_from_jsonl(jsonl_path: Path) -> str:
    """JSONL 마지막 부분에서 모델 ID를 읽는다."""
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            f.seek(0, 2)
            fsize = f.tell()
            f.seek(max(0, fsize - 50_000))
            chunk = f.read()
        for line in reversed(chunk.strip().split("\n")[-10:]):
            try:
                entry = json.loads(line)
                model = entry.get("message", {}).get("model", "")
                if model:
                    return model
            except (json.JSONDecodeError, AttributeError):
                continue
    except Exception:
        pass
    return "claude-opus-4-6"


def model_display_name(model_id: str) -> str:
    if "opus" in model_id:
        return "Opus 4.6"
    if "sonnet" in model_id:
        return "Sonnet 4.6"
    if "haiku" in model_id:
        return "Haiku 4.5"
    return model_id


def call_ccusage(jsonl_path: Path, project_dir: Path, model_id: str) -> str:
    """ccusage statusline 호출. cwd=JSONL디렉토리, encoding=utf-8."""
    display = model_display_name(model_id)
    input_json = json.dumps({
        "session_id": jsonl_path.stem,
        "transcript_path": jsonl_path.name,
        "cwd": "Q:\\",
        "model": {"id": model_id, "display_name": display},
        "workspace": {"path": "Q:\\", "current_dir": "Q:\\", "project_dir": "Q:\\"},
    })
    try:
        r = subprocess.run(
            [NPX, "ccusage", "statusline", "--no-color"],
            input=input_json,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            cwd=str(project_dir),
            creationflags=_NO_WINDOW,   # 2026-04-28: cmd 창 깜빡임 차단
        )
        return r.stdout.strip()
    except Exception:
        return ""


def parse_context_pct(line: str):
    """ccusage 출력에서 컨텍스트 사용률(%) 추출."""
    m = re.search(r"\((\d+)%\)", line)
    return int(m.group(1)) if m else None


def recommend(pct, display: str) -> str:
    if pct is None:
        return ""
    if pct < 40 and "Opus" in display:
        return "💡Sonnet추천"
    if pct < 70:
        return ""
    if pct < 85:
        return "⚠️/compact"
    return "🚨새세션"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    jsonl_path, project_dir = find_session()
    if not jsonl_path:
        print("🤖 ? | 세션없음")
        return

    model_id = read_model_from_jsonl(jsonl_path)
    display = model_display_name(model_id)
    raw = call_ccusage(jsonl_path, project_dir, model_id)

    if raw:
        pct = parse_context_pct(raw)
        rec = recommend(pct, display)
        print(f"{raw} | {rec}" if rec else raw)
    else:
        print(f"🤖 {display} | 🧠 데이터없음")


if __name__ == "__main__":
    main()
