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


def deny(reason: str) -> None:
    """PreToolUse 차단 응답 출력 후 종료."""
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
                deny(f"Bash 위험 패턴 차단: {desc}\n명령어: {command[:200]}")
            else:
                warn(f"Bash 위험 패턴 경고: {desc}\n명령어: {command[:200]}")


def check_write_edit(tool_name: str, tool_input: dict):
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return

    # 허용 경로 외부 쓰기
    if not is_allowed_write_path(file_path):
        deny(f"{tool_name} 허용 경로 외부 쓰기 차단: {file_path}")

    # 특정 위험 경로 패턴
    for pattern, desc in WRITE_BLOCK_PATTERNS:
        if re.search(pattern, file_path, re.IGNORECASE):
            deny(f"{tool_name} 차단: {desc} | 경로: {file_path}")

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
