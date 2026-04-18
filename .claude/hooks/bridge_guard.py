"""
bridge_guard.py - PreToolUse hook for BRIDGE project
======================================================
Claude Code가 Bash/Write/Edit/WebFetch 실행 직전에 호출됨.

보호 항목:
  Bash   : rm -rf, 원격 코드 실행, force push, 프로덕션 API 쓰기, DB 파괴 SQL
  Write  : 허용 경로 외부 쓰기, .env 직접 수정, 시스템 디렉터리
  Edit   : 동일 (Write와 같은 경로 규칙)
  WebFetch: Production URL + 쓰기 메서드 (POST/PATCH/DELETE)

stdin : {"tool_name": "...", "tool_input": {...}, "session_id": "..."}
stdout: 차단 시 {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                        "permissionDecision": "deny",
                                        "permissionDecisionReason": "..."}}
        경고 시 {"systemMessage": "..."}
        정상 시 아무것도 없음 (exit 0)
"""

import json
import re
import sys
import time
import uuid
import urllib.request
import unicodedata
from pathlib import Path
from datetime import datetime

# ── 설정 ──────────────────────────────────────────────────────────────────────

ALLOWED_WRITE_ROOTS = [
    Path(r"Q:\Claudework"),
    Path(r"C:\Users\Scarlett\.claude"),
    Path(r"Q:\openrun_api"),
    Path(r"Q:\openrun_app"),
    Path(r"Q:\openrun_admin"),
    Path(r"Q:\wealth_manager"),
]

LOG_PATH = Path(r"Q:\Claudework\bridge base\.claude\hooks\bridge_guard.log")

# Production API — 쓰기 요청 차단 대상
PROD_API_HOSTS = [
    "bridge-n7hk.onrender.com",
    "bridgejob.co.kr",
    "api.bridgejob.co.kr",
    "bridge-chi-lime.vercel.app",
    "discord-9b61.onrender.com",
]


# ── Bash 위험 패턴 ────────────────────────────────────────────────────────────

# (패턴, 설명, block=True/False) — block=False 는 경고만
BASH_RULES: list[tuple[str, str, bool]] = [
    # 파괴적 삭제 — 명령 경계(^, &&, ||, ;, |, 줄바꿈) 다음에 오는 것만 차단
    # Python -c "..." 내부 문자열, 커밋 메시지 등 오탐 방지
    (r"(?:^|&&|\|\||;|\n)\s*rm\s+-[^\s]*r[^\s]*\s+[/\\]", "rm -rf 절대경로 삭제", True),
    (r"(?:^|&&|\|\||;|\n)\s*rm\s+-rf\b", "rm -rf 감지", True),
    (r"(?:^|&&|\|\||;|\n)\s*rmdir\s+/s\b", "rmdir /s 감지", True),
    (r"(?:^|&&|\|\||;|\n)\s*del\s+/[fqs]", "del /f 강제삭제 감지", True),

    # 원격 코드 실행
    (r"curl\s+.+\|\s*(bash|sh|python|powershell)", "원격 스크립트 실행 (curl|pipe)", True),
    (r"wget\s+.+\|\s*(bash|sh|python)", "원격 스크립트 실행 (wget|pipe)", True),
    (r"Invoke-Expression\s*\(.*Download", "IEX 원격 실행 감지", True),

    # Git 파괴적 작업
    (r"git\s+push\s+.*--force\s+.*(?:main|master)", "main/master force push 차단", True),
    (r"git\s+push\s+.*-f\s+.*(?:main|master)", "main/master -f push 차단", True),
    (r"git\s+reset\s+--hard\s+HEAD~[2-9]", "git reset --hard 다중 커밋 롤백", True),
    (r"git\s+filter-repo", "git filter-repo (히스토리 재작성) — 사용자 확인 필요", False),

    # DB 파괴 SQL — sqlite3 직접 실행 또는 SQL 파일 실행 시만 차단
    # 커밋 메시지/주석 오탐 방지: sqlite3 명령 컨텍스트 확인
    (r"sqlite3\b.+DROP\s+TABLE", "sqlite3 DROP TABLE 감지", True),
    (r"sqlite3\b.+DELETE\s+FROM\s+\w+\s*;", "sqlite3 WHERE 없는 DELETE 감지", True),
    (r"sqlite3\b.+TRUNCATE\s+TABLE", "sqlite3 TRUNCATE TABLE 감지", True),

    # 시스템/레지스트리 변경
    (r"reg\s+(add|delete)\s+", "레지스트리 수정 감지", True),
    (r"net\s+(user|localgroup)\s+.+/add", "계정/그룹 추가 감지", True),
    (r"netsh\s+", "네트워크 설정 변경 감지 (netsh)", True),
    (r"diskpart\b", "diskpart 디스크 조작 감지", True),
    (r"format\s+[A-Za-z]:", "디스크 포맷 감지", True),

    # Production 직접 호출 (curl POST/PATCH/DELETE to prod)
    (
        r"curl\s+.+(?:" + "|".join(re.escape(h) for h in PROD_API_HOSTS) + r").+"
        r"(?:-X\s+(?:POST|PATCH|DELETE|PUT)|--data|-d\s+)",
        "프로덕션 API 쓰기 요청 차단",
        True,
    ),

    # master.db 직접 삭제 — 명령 경계
    (r"(?:^|&&|\|\||;|\n)\s*(rm|del).+master\.db\b", "master.db 삭제 시도 차단", True),
]


# ── Write/Edit 위험 경로 ──────────────────────────────────────────────────────

WRITE_BLOCK_PATTERNS: list[tuple[str, str]] = [
    # 시스템 디렉터리
    (r"^[Cc]:[/\\]Windows[/\\]", "Windows 시스템 디렉터리 쓰기 차단"),
    (r"^[Cc]:[/\\]Program Files", "Program Files 쓰기 차단"),
    # .env 직접 수정 (pw.py 경유해야 함)
    (r"[/\\]\.env$", ".env 직접 수정 금지 — pw.py GUI 경유 필요"),
    # DB 파일 덮어쓰기
    (r"master\.db$", "master.db 직접 Write 차단"),
    # 키 파일
    (r"\.bridge\.key$", ".bridge.key 직접 Write 차단"),
    (r"\.vault[/\\]", ".vault 디렉터리 직접 Write 차단"),
]


# ── WebFetch 위험 패턴 ────────────────────────────────────────────────────────

WEBFETCH_WRITE_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


# ── 공통 유틸 ────────────────────────────────────────────────────────────────

def log(msg: str):
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
    except Exception:
        pass


# ── Telegram 승인 시스템 ──────────────────────────────────────────────────────

_TG_TIMEOUT = 86400   # 24시간 — 보스가 답할 때까지 무한 대기
_DB_PATH = Path(r"Q:\Claudework\bridge base\master.db")


def _tg_token() -> str:
    """BX vault에서 Telegram 토큰 읽기."""
    try:
        import sqlite3 as _sql
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))
        from bx import _read as bx_read
        return bx_read("TELEGRAM_BOT_TOKEN") or ""
    except Exception:
        return ""


def _tg_subscribers() -> list[int]:
    try:
        import sqlite3
        conn = sqlite3.connect(str(_DB_PATH))
        rows = conn.execute("SELECT chat_id FROM tg_alert_subscribers WHERE active=1").fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def _tg_post(token: str, method: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def _ai_review(danger_type: str, command: str) -> tuple[bool, str]:
    """Claude Haiku가 위험 명령 검토 — (승인여부, 이유) 반환."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))
        from bx import _read as bx_read
        api_key = bx_read("ANTHROPIC_API_KEY")
    except Exception:
        return False, "API key 없음"

    if not api_key:
        return False, "API key 없음"

    prompt = f"""당신은 BRIDGE 프로젝트 자동 보안 관리자입니다.
아래 명령어가 실행되려고 합니다. 안전한지 판단해주세요.

위험 유형: {danger_type}
명령어:
{command[:600]}

판단 기준:
- 복구 가능 / 로컬 개발·테스트 목적 → APPROVE
- master.db 영구 손실 위험 → DENY
- main/master 브랜치 파괴 위험 → DENY
- 운영 서버(bridge-n7hk.onrender.com) 데이터 삭제 → DENY
- .next 캐시·임시파일 정리 → APPROVE
- git reset (로컬 only) → APPROVE

첫 단어를 반드시 APPROVE 또는 DENY로 쓰고, 짧은 이유를 한 줄로.
예: APPROVE - .next 캐시 삭제, 복구 가능
예: DENY - master.db 직접 삭제, 운영 DB 손실"""

    try:
        data = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 80,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
        answer = resp["content"][0]["text"].strip()
        approved = answer.upper().startswith("APPROVE")
        return approved, answer
    except Exception as e:
        return False, f"AI 검토 실패: {e}"


def _tg_ask(danger_type: str, command_preview: str) -> bool:
    """위험 작업을 텔레그램으로 묻고 결과 반환 (True=허용, False=거절)."""
    token = _tg_token()
    if not token:
        return False

    subs = _tg_subscribers()
    if not subs:
        return False

    rid = str(uuid.uuid4())[:8]
    preview = command_preview[:250] + ("..." if len(command_preview) > 250 else "")
    now = time.strftime("%H:%M")

    msg = (
        f"🚨 확인 필요해요! ({now})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>{danger_type}</b>\n\n"
        f"<code>{preview}</code>\n\n"
        f"시간 나실 때 <b>응</b> 또는 <b>아니</b> 로 답장해주세요\n"
        f"답장 전까지 작업은 멈춰서 기다리고 있을게요 🙂"
    )
    keyboard = {"inline_keyboard": [[
        {"text": "✅ 승인", "callback_data": f"allow_{rid}"},
        {"text": "❌ 거절", "callback_data": f"deny_{rid}"},
    ]]}

    # 메시지 발송
    msg_info = []
    for cid in subs[:1]:
        try:
            resp = _tg_post(token, "sendMessage", {
                "chat_id": cid,
                "text": msg,
                "parse_mode": "HTML",
                "reply_markup": keyboard,
            })
            if resp.get("ok"):
                msg_info.append((cid, resp["result"]["message_id"]))
        except Exception:
            pass

    if not msg_info:
        return False

    # 현재 offset 확보 (이전 업데이트 skip)
    try:
        resp = _tg_post(token, "getUpdates", {"limit": 1, "timeout": 0})
        updates = resp.get("result", [])
        offset = (updates[-1]["update_id"] + 1) if updates else 0
    except Exception:
        offset = 0

    # 승인 키워드
    YES = {"응", "ㅇ", "예", "yes", "y", "ok", "오케", "오케이", "해", "해줘", "고", "go",
           "승인", "허용", "그래", "ㄱ", "ㄱㄱ", "굿", "좋아", "좋아요", "넵", "넴"}
    NO  = {"아니", "ㄴ", "노", "no", "n", "안돼", "안돼요", "거절", "스톱", "stop",
           "하지마", "취소", "cancel", "말아", "말아줘", "싫어"}

    # 45초간 텍스트 메시지 polling
    deadline = time.time() + _TG_TIMEOUT
    result = None
    while time.time() < deadline and result is None:
        try:
            remaining = max(1, int(deadline - time.time()))
            poll_t = min(remaining, 10)
            resp = _tg_post(token, "getUpdates", {
                "offset": offset,
                "timeout": poll_t,
                "allowed_updates": ["message"],
            })
            for upd in resp.get("result", []):
                offset = upd["update_id"] + 1
                message = upd.get("message", {})
                # 구독자 chat_id에서 온 메시지만
                if message.get("chat", {}).get("id") not in subs:
                    continue
                text = message.get("text", "").strip().lower()
                if text in YES:
                    result = True
                elif text in NO:
                    result = False
                if result is not None:
                    label = "✅ 승인됐어요!" if result else "❌ 거절됐어요!"
                    try:
                        cid, mid = msg_info[0]
                        _tg_post(token, "editMessageText", {
                            "chat_id": cid, "message_id": mid,
                            "text": f"{label}\n\n{msg}",
                            "parse_mode": "HTML",
                        })
                        # 답장 확인 메시지
                        _tg_post(token, "sendMessage", {
                            "chat_id": message["chat"]["id"],
                            "text": label,
                        })
                    except Exception:
                        pass
                    break
        except Exception:
            time.sleep(1)

    if result is None:
        # 24시간 초과 — 사실상 없는 케이스지만 혹시 모르니 로그만
        log("TG_WAIT_TIMEOUT 24h 초과")
        return False

    return result


def deny(reason: str, ask_telegram: bool = False, cmd_preview: str = "") -> None:
    """PreToolUse 차단 응답 출력 후 종료.

    흐름:
      1. AI 관리자봇(Haiku)이 먼저 검토
         → APPROVE : 바로 허용 (보스 알림 없음)
         → DENY    : 보스 텔레그램으로 에스컬레이션
      2. 보스가 "응/아니" 답장
         → 응  : 허용
         → 아니 / 타임아웃 : 최종 차단
    """
    if ask_telegram and cmd_preview:
        # ── 1단계: AI 관리자봇 검토 ─────────────────
        ai_ok, ai_reason = _ai_review(reason, cmd_preview)
        log(f"AI_REVIEW [{('OK' if ai_ok else 'NO')}] {reason} | {ai_reason}")

        if ai_ok:
            # AI가 안전하다고 판단 → 바로 통과
            log(f"AI_APPROVED {reason}")
            sys.exit(0)

        # ── 2단계: AI가 NO → 보스에게 에스컬레이션 ──
        log(f"TG_ESCALATE {reason} | AI: {ai_reason}")

        # Telegram 메시지에 AI 판단 이유 포함
        enriched = f"{cmd_preview}\n\n🤖 AI관리자: {ai_reason}"
        approved = _tg_ask(reason, enriched)
        if approved:
            log(f"BOSS_APPROVED {reason}")
            sys.exit(0)
        log(f"BOSS_DENIED {reason}")

    log(f"DENY {reason}")
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"[bridge_guard] {reason}",
        }
    }
    print(json.dumps(out, ensure_ascii=False), flush=True)
    sys.exit(0)


def warn(reason: str) -> None:
    """경고만 출력 (차단하지 않음)."""
    log(f"WARN {reason}")
    print(json.dumps({"systemMessage": f"[bridge_guard] {reason}"}, ensure_ascii=False), flush=True)


def is_allowed_write_path(file_path: str) -> bool:
    try:
        resolved = Path(file_path).resolve()
        return any(
            str(resolved).startswith(str(root.resolve()))
            for root in ALLOWED_WRITE_ROOTS
        )
    except Exception:
        return False


# ── Bash 전처리: 커밋 메시지 등 텍스트 콘텐츠 제거 ─────────────────────────

def _strip_heredoc(command: str) -> str:
    """heredoc 본문(<<'EOF'...EOF) 제거 — 커밋 메시지 안의 패턴 오탐 방지."""
    # <<'WORD' 또는 <<"WORD" 또는 <<WORD 패턴
    return re.sub(r"<<['\"]?\w+['\"]?\n.*?^\w+\s*$", "", command,
                  flags=re.DOTALL | re.MULTILINE)


def _strip_git_message(command: str) -> str:
    """-m "..." 또는 -m $'...' 커밋 메시지 본문 제거."""
    # git commit -m "...(멀티라인)..."
    command = re.sub(r'git\s+commit\b[^\n]*-m\s+"[^"]*"', "git commit -m MSG_REMOVED", command, flags=re.DOTALL)
    command = re.sub(r"git\s+commit\b[^\n]*-m\s+'[^']*'", "git commit -m MSG_REMOVED", command, flags=re.DOTALL)
    return command


def _normalize_unicode(text: str) -> str:
    """Unicode 전각/유사 문자를 ASCII로 정규화.

    ｒm → rm, ／ → /, ０ → 0 등 전각 문자 우회 차단.
    NFKC: 호환 분해 + 정규 합성 (전각→반각 포함).
    """
    return unicodedata.normalize("NFKC", text)


def _preprocess_bash(command: str) -> str:
    """스캔 전 텍스트성 콘텐츠 제거 + Unicode 정규화 — 오탐/우회 방지."""
    command = _normalize_unicode(command)   # ① 전각 문자 정규화
    command = _strip_heredoc(command)       # ② heredoc 본문 제거
    command = _strip_git_message(command)   # ③ 커밋 메시지 제거
    return command


# ── Git 계정 매핑 ─────────────────────────────────────────────────────────────

# (경로 키워드, 계정, 용도)
GIT_ACCOUNT_MAP = [
    ("openrun",        "App-kr",      "openrun-app / openrun-api"),
    ("Game Discord",   "dobby-kr",    "DJ티모 Discord 봇"),
    ("bridge-jobs",    "koreadobby",  "bridge-jobs 프론트"),
    ("bridge base",    "koreadobby",  "BRIDGE 메인"),
    ("bridge",         "koreadobby",  "BRIDGE"),
    ("Dobby",          "dobby-kr",    "DJ티모"),
]

GIT_AUTH_CMDS = re.compile(
    r"\b(git\s+(push|pull|fetch|clone)|gh\s+(auth|repo|pr|release))\b",
    re.IGNORECASE,
)


def _detect_git_account(command: str) -> tuple[str, str] | None:
    """명령어에서 어떤 계정이 필요한지 추론. (account, purpose) 반환."""
    # 명령어 내 경로 또는 URL에서 힌트 추출
    for keyword, account, purpose in GIT_ACCOUNT_MAP:
        if keyword.lower() in command.lower():
            return account, purpose
    # 힌트 없으면 None (알 수 없음)
    return None


def check_git_account(tool_input: dict):
    """git push/pull/fetch 등 네트워크 git 명령 전 계정 경고."""
    command = tool_input.get("command", "")
    if not GIT_AUTH_CMDS.search(command):
        return
    result = _detect_git_account(command)
    if result:
        account, purpose = result
        warn(f"⚠️  Git 계정 필요 → **{account}** ({purpose})\n"
             f"로그인 확인: gh auth status | 전환: gh auth login -h github.com --web")
    else:
        warn("⚠️  Git 네트워크 명령 감지 — 어떤 계정인지 확인하세요\n"
             "계정 확인: gh auth status")


# ── 도구별 검사 ──────────────────────────────────────────────────────────────

def check_bash(tool_input: dict):
    command = tool_input.get("command", "")
    scan_target = _preprocess_bash(command)
    for pattern, desc, block in BASH_RULES:
        if re.search(pattern, scan_target, re.IGNORECASE):
            if block:
                # 텔레그램으로 승인 요청 → 거절/타임아웃이면 차단
                deny(
                    f"Bash 위험 패턴: {desc}",
                    ask_telegram=True,
                    cmd_preview=command,
                )
            else:
                warn(f"Bash 위험 패턴 경고: {desc}\n명령어: {command[:200]}")


def check_write_edit(tool_name: str, tool_input: dict):
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return

    # 허용 경로 외부 쓰기
    if not is_allowed_write_path(file_path):
        deny(f"{tool_name} 허용 경로 외부 쓰기", ask_telegram=True, cmd_preview=file_path)

    # 특정 위험 경로 패턴
    for pattern, desc in WRITE_BLOCK_PATTERNS:
        if re.search(pattern, file_path, re.IGNORECASE):
            deny(f"{tool_name} 위험 경로: {desc}", ask_telegram=True, cmd_preview=file_path)

    # Write일 때 content에 하드코딩 시크릿 감지
    if tool_name == "Write":
        content = tool_input.get("content", "")
        _check_hardcoded_secrets(content, file_path)


def _check_hardcoded_secrets(content: str, file_path: str):
    """코드 내 하드코딩 시크릿 패턴 감지 (경고)."""
    secret_patterns = [
        (r'(api[_-]?key|secret|password|passwd|token)\s*=\s*["\'][A-Za-z0-9+/]{20,}["\']',
         "하드코딩 시크릿 감지"),
        (r'sk-[A-Za-z0-9]{40,}', "Anthropic API Key 패턴"),
        (r'AIza[A-Za-z0-9_-]{35}', "Google API Key 패턴"),
        (r'ghp_[A-Za-z0-9]{36}', "GitHub PAT 패턴"),
    ]
    for pattern, desc in secret_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            warn(f"Write 시크릿 감지: {desc} | 파일: {file_path} | pw.py GUI 경유 권장")
            break  # 첫 번째 감지만 경고


def check_webfetch(tool_input: dict):
    url = tool_input.get("url", "")
    method = tool_input.get("method", "GET").upper()

    # Production 쓰기 요청
    if method in WEBFETCH_WRITE_METHODS:
        for host in PROD_API_HOSTS:
            if host in url:
                deny(f"WebFetch 프로덕션 쓰기 차단: {method} {url}")


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name == "Bash":
        check_git_account(tool_input)
        check_bash(tool_input)
    elif tool_name in ("Write", "Edit"):
        check_write_edit(tool_name, tool_input)
    elif tool_name == "WebFetch":
        check_webfetch(tool_input)

    sys.exit(0)


if __name__ == "__main__":
    main()
