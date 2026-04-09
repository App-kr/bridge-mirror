"""
tools/claude_bridge.py
======================
Claude Code ↔ Claude API 자동 브리지 (리뷰어 에이전트)

동작:
  Stop 훅 → 최근 대화 읽기 → Claude API 리뷰어에 전송 → systemMessage로 표시

수동 실행:
  python tools/claude_bridge.py "에러 텍스트 or 코드"
  python tools/claude_bridge.py --last   (마지막 응답만 리뷰)

ANTHROPIC_API_KEY: BX 또는 환경변수에서 자동 로드
"""

import sys, os, json, re
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE = Path(__file__).resolve().parent.parent

# ── 키 로드 ──────────────────────────────────────────────────────────────
def _bx_read(key: str) -> str:
    sys.path.insert(0, str(BASE))
    try:
        from tools.bx import _read
        return _read(key) or ""
    except Exception:
        return ""

def _get_api_key() -> str:
    return (os.environ.get("ANTHROPIC_API_KEY") or _bx_read("ANTHROPIC_API_KEY")).strip()

# ── 트랜스크립트 읽기 ────────────────────────────────────────────────────
def _get_last_exchange(session_id: str = None, max_chars: int = 8000) -> str:
    """최근 user→assistant 교환 1쌍을 읽어 반환."""
    projects_dir = Path.home() / ".claude" / "projects"

    # session_id가 있으면 해당 파일, 없으면 가장 최근 파일
    if session_id:
        jsonl_files = list(projects_dir.rglob(f"{session_id}.jsonl"))
    else:
        jsonl_files = sorted(projects_dir.rglob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)

    if not jsonl_files:
        return ""

    target = jsonl_files[0]
    lines = target.read_text(encoding="utf-8", errors="replace").strip().splitlines()

    # 마지막 assistant 메시지와 그 직전 user 메시지 추출
    messages = []
    for line in reversed(lines):
        try:
            entry = json.loads(line)
            msg = entry.get("message", {})
            role = msg.get("role", "")
            content = msg.get("content", "")
            if isinstance(content, list):
                # content 배열에서 text 추출
                text = " ".join(
                    block.get("text", "") for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                )
            elif isinstance(content, str):
                text = content
            else:
                continue
            if text.strip() and role in ("user", "assistant"):
                messages.insert(0, (role, text.strip()))
                if len(messages) >= 4:  # user+assistant 2쌍이면 충분
                    break
        except Exception:
            continue

    result = []
    for role, text in messages[-4:]:
        label = "사용자" if role == "user" else "Claude Code"
        result.append(f"[{label}]\n{text[:3000]}")

    combined = "\n\n".join(result)
    return combined[:max_chars]


# ── Claude API 리뷰어 호출 ──────────────────────────────────────────────
REVIEWER_SYSTEM = """당신은 Claude Code(터미널 AI)의 작업을 검토하는 시니어 리뷰어입니다.

역할:
- Claude Code의 최근 응답에서 버그·에러·잘못된 접근을 찾아냄
- 더 나은 방향이 있으면 구체적으로 제시
- 이미 올바르면 "✅ 검토 통과" 한 줄로 끝냄
- 불필요한 칭찬 없이 핵심만 말함
- 한국어로 답변

출력 형식:
🔍 발견: [문제 요약 또는 "없음"]
💡 개선: [구체적 제안 또는 "없음"]
⚡ 다음 단계: [권장 액션 1줄]"""


def _call_reviewer(content: str, api_key: str = "") -> str:
    """claude CLI --print 모드로 리뷰어 호출 (Claude Max 구독 사용).

    ⚠️ 중요: claude --print에 멀티라인 인수를 전달하면 hanging됨.
    → 프롬프트를 단일 라인으로 평탄화하여 전달.
    """
    import subprocess

    # 대화 내용을 단일 라인으로 압축 (최대 300자 — 너무 길면 응답 지연)
    flat_content = content.replace("\n", " ").replace("\r", "")[:300]

    # 간결한 단일라인 프롬프트 (이모지 제거 — 응답 속도 개선)
    prompt = (
        "당신은 시니어 코드 리뷰어입니다. 한국어로 답하세요. "
        "형식: 발견:[문제요약/없음] 개선:[제안/없음] "
        "다음 Claude Code 작업을 검토하세요: "
        + flat_content
    )

    # 홈 디렉토리에서 실행 — 프로젝트 CLAUDE.md 자동 로딩 방지
    run_dir = str(Path.home())
    try:
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=85,
            cwd=run_dir
        )
        out = result.stdout.strip()
        if out:
            return out
        err = result.stderr.strip()
        if err:
            return f"리뷰 오류: {err[:200]}"
        return "리뷰 결과 없음"
    except subprocess.TimeoutExpired:
        return "⏱ 리뷰 타임아웃 (85초 초과)"
    except FileNotFoundError:
        return "claude CLI를 찾을 수 없음"
    except Exception as e:
        return f"리뷰 실패: {e}"


# ── 메인 ────────────────────────────────────────────────────────────────
def main():
    api_key = _get_api_key()
    if not api_key:
        # API 키 없으면 조용히 종료 (훅 실패 방지)
        sys.exit(0)

    args = sys.argv[1:]

    # stdin에서 세션 정보 읽기 (Stop 훅에서 호출 시)
    session_id = None
    try:
        if not sys.stdin.isatty():
            hook_data = json.loads(sys.stdin.read() or "{}")
            session_id = hook_data.get("session_id")
    except Exception:
        pass

    # 수동 텍스트 입력
    if args and args[0] not in ("--last", "--auto"):
        content = " ".join(args)
    else:
        content = _get_last_exchange(session_id)

    if not content.strip():
        sys.exit(0)

    # 너무 짧은 교환은 스킵 (인사말 등)
    if len(content) < 100:
        sys.exit(0)

    review = _call_reviewer(content, api_key)

    # Stop 훅 → JSON systemMessage 출력
    # 수동 실행 → 일반 텍스트 출력
    if not sys.stdin.isatty() or "--auto" in args:
        output = {"systemMessage": f"🤖 리뷰어: {review}"}
        print(json.dumps(output, ensure_ascii=False))
    else:
        print("\n── 리뷰어 분석 ──────────────────")
        print(review)
        print("─────────────────────────────────\n")


if __name__ == "__main__":
    main()
