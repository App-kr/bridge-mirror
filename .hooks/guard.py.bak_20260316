#!/usr/bin/env python3
"""
guard.py — PreToolUse 보안 게이트
PreToolUse hook으로 실행됨
stdin으로 JSON 수신 → hookSpecificOutput 반환 (Claude Code 최신 형식)

수정 이력:
  2026-03-09 — deprecated {decision} 형식 → hookSpecificOutput 형식으로 교체
               WRITE_OPS 체크 cmd_lower 통일
"""
import sys, json

def approve():
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow"
        }
    }))
    sys.exit(0)

def block(reason: str):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"🛡️ BRIDGE guard.py 차단: {reason}"
        }
    }, ensure_ascii=False))
    sys.exit(0)

try:
    data = json.load(sys.stdin)
    cmd = data.get("tool_input", {}).get("command", "")
except Exception:
    # stdin 파싱 실패 시 통과 (Claude Code 정상작동 우선)
    approve()

# ── 절대 차단 패턴 ───────────────────────────────
BLOCK = [
    ("rm -rf /",                               "루트 전체 삭제 시도"),
    ("rm -rf ~",                               "홈디렉토리 삭제 시도"),
    ("rm -rf c:",                              "C드라이브 삭제 시도"),
    ("del /f /s /q c:\\windows",               "Windows 시스템 삭제"),
    ("del /f /s /q c:\\users\\scarlett\\appdata", "AppData 삭제"),
    ("format c:",                              "C드라이브 포맷"),
    ("format d:",                              "D드라이브 포맷"),
    ("> /dev/sda",                             "디스크 직접 쓰기"),
    ("reg delete hklm",                        "시스템 레지스트리 삭제"),
    ("bcdedit",                                "부트설정 변경"),
]

cmd_lower = cmd.lower().replace("\\\\", "\\")

for pattern, reason in BLOCK:
    if pattern in cmd_lower:
        block(reason)

# ── Q드라이브 외부 쓰기 차단 ────────────────────
# cmd_lower 통일 (원본/소문자 혼용 버그 수정)
WRITE_OPS = [" > ", ">>", "tee "]
FORBIDDEN = [
    "c:\\windows",
    "c:\\program files",
    "c:\\users\\scarlett\\desktop",
    "c:\\users\\scarlett\\documents",
]

if any(w in cmd_lower for w in WRITE_OPS):
    for fp in FORBIDDEN:
        if fp in cmd_lower:
            block(f"Q드라이브 외부 쓰기: {fp}")

# ── 통과 ─────────────────────────────────────────
approve()
