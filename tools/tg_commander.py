"""
BRIDGE Telegram Commander — 대화형 봇 데몬
==========================================
Telegram에서 BRIDGE 작업을 직접 지시하고 결과를 받아볼 수 있는 인터랙티브 봇.

실행: python tools/tg_commander.py --daemon
명령:
  /status       — 서버·DB·파이프라인 현황
  /resume [id]  — 이력서 변환 (후보자 ID)
  /pipeline     — 파이프라인 큐 상태
  /apply_test   — /apply 페이지 테스트 안내
  /git          — 최근 커밋 5개
  /db           — DB 통계
  /watcher      — Pipeline Watcher 상태
  /help         — 도움말
  그 외 텍스트  — Claude에 전달 (자동 응답)
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "master.db"
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

try:
    from bx import _read as bx_read
    TOKEN = bx_read("TELEGRAM_BOT_TOKEN")
except Exception:
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

if not TOKEN:
    print("[tg_commander] TELEGRAM_BOT_TOKEN 없음 — 종료")
    sys.exit(1)

_PY_Q = PROJECT_ROOT.parent.parent / "Phtyon 3" / "python.exe"
PYTHON = str(_PY_Q) if _PY_Q.exists() else sys.executable
API_BASE = f"https://api.telegram.org/bot{TOKEN}"

# 마지막 처리한 update_id
offset_file = PROJECT_ROOT / ".claude" / "tg_offset.txt"

# deploy_gate IPC 파일: deploy_gate.py가 이 파일을 읽어 yes/no 판단
GATE_IPC_FILE = PROJECT_ROOT / ".claude" / "tg_gate_response.json"


# ── 텔레그램 API ──────────────────────────────────────────────
def tg_get(method: str, params: dict = None):
    url = f"{API_BASE}/{method}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=35) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[tg] GET {method} 실패: {e}")
        return {}


def tg_post(method: str, data: dict):
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/{method}",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[tg] POST {method} 실패: {e}")
        return {}


def send(chat_id: int, text: str, parse_mode="HTML"):
    # 4096자 분할
    for i in range(0, len(text), 4000):
        tg_post("sendMessage", {
            "chat_id": chat_id,
            "text": text[i:i+4000],
            "parse_mode": parse_mode,
        })


# ── 구독자 목록 ──────────────────────────────────────────────
def get_subscribers():
    try:
        conn = sqlite3.connect(str(DB_PATH))
        rows = conn.execute(
            "SELECT chat_id FROM tg_alert_subscribers WHERE active=1"
        ).fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def broadcast(text: str):
    for cid in get_subscribers():
        send(cid, text)


# ── 커맨드 핸들러 ──────────────────────────────────────────────
def cmd_help(chat_id: int, _args: str):
    send(chat_id, (
        "🤖 <b>BRIDGE Commander</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "/status       — 전체 현황 요약\n"
        "/pipeline     — 파이프라인 큐 상태\n"
        "/watcher      — Pipeline Watcher 상태\n"
        "/resume [id]  — 이력서 변환 (후보자 ID)\n"
        "/git          — 최근 커밋 5개\n"
        "/db           — DB 통계\n"
        "/apply_test   — Apply 페이지 테스트 링크\n"
        "/run [cmd]    — 쉘 명령 실행 (간단)\n"
        "/help         — 이 도움말\n\n"
        "💬 자유 텍스트 → 그대로 실행 결과 반환"
    ))


def cmd_status(chat_id: int, _args: str):
    lines = ["📊 <b>BRIDGE 현황</b>\n━━━━━━━━━━━━━━━━━━━━━━━━"]

    # DB 통계
    try:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.execute("SELECT COUNT(*) FROM candidates WHERE is_deleted=0").fetchone()[0]
        j = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_deleted=0").fetchone()[0]
        i = conn.execute("SELECT COUNT(*) FROM client_inquiries").fetchone()[0]
        conn.close()
        lines.append(f"📁 DB: 후보 <b>{c}</b>명 | 공고 <b>{j}</b>건 | 문의 <b>{i}</b>건")
    except Exception as e:
        lines.append(f"DB 조회 실패: {e}")

    # Pipeline 큐
    try:
        pdb = PROJECT_ROOT / "pipeline_queue.db"
        if pdb.exists():
            conn2 = sqlite3.connect(str(pdb))
            q = conn2.execute("SELECT status, COUNT(*) FROM pipeline_queue GROUP BY status").fetchall()
            conn2.close()
            q_str = " | ".join(f"{s}:{n}" for s, n in q) if q else "비어있음"
            lines.append(f"⚙️ Pipeline: {q_str}")
        else:
            lines.append("⚙️ Pipeline DB: 없음")
    except Exception as e:
        lines.append(f"Pipeline 조회 실패: {e}")

    # Watcher Task Scheduler 상태
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "(Get-ScheduledTask -TaskName 'BRIDGE_PipelineWatcher').State"],
            capture_output=True, text=True, timeout=5
        )
        state = result.stdout.strip() or "알 수 없음"
        lines.append(f"👁️ Watcher: {state}")
    except Exception:
        lines.append("👁️ Watcher: 확인 불가")

    # Git HEAD
    try:
        result = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "log", "--oneline", "-1"],
            capture_output=True, text=True, timeout=5
        )
        lines.append(f"🔀 Git: {result.stdout.strip()}")
    except Exception:
        pass

    lines.append(f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    send(chat_id, "\n".join(lines))


def cmd_pipeline(chat_id: int, _args: str):
    pdb = PROJECT_ROOT / "pipeline_queue.db"
    if not pdb.exists():
        send(chat_id, "❌ pipeline_queue.db 없음")
        return
    try:
        conn = sqlite3.connect(str(pdb))
        rows = conn.execute(
            "SELECT id, filename, status, retry_count, created_at FROM pipeline_queue ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
        conn.close()
        if not rows:
            send(chat_id, "📭 파이프라인 큐가 비어있습니다")
            return
        lines = ["⚙️ <b>Pipeline 큐 (최근 20건)</b>\n━━━━━━━━━━━━━━━━━━━━━━━━"]
        for r in rows:
            lines.append(f"[{r[0]}] {r[1]} | <b>{r[2]}</b> | retry:{r[3]} | {r[4]}")
        send(chat_id, "\n".join(lines))
    except Exception as e:
        send(chat_id, f"❌ 조회 실패: {e}")


def cmd_watcher(chat_id: int, _args: str):
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-ScheduledTask -TaskName 'BRIDGE_PipelineWatcher' | Select-Object TaskName,State,LastRunTime,NextRunTime | ConvertTo-Json"],
            capture_output=True, text=True, timeout=8
        )
        data = json.loads(result.stdout)
        msg = (
            f"👁️ <b>Pipeline Watcher</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"상태: <b>{data.get('State','?')}</b>\n"
            f"마지막 실행: {data.get('LastRunTime','?')}\n"
            f"다음 실행: {data.get('NextRunTime','없음(데몬)')}"
        )
    except Exception as e:
        msg = f"⚙️ Watcher 조회 실패: {e}"
    send(chat_id, msg)


def cmd_git(chat_id: int, _args: str):
    try:
        result = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "log", "--oneline", "-5"],
            capture_output=True, text=True, timeout=5
        )
        send(chat_id, f"🔀 <b>최근 커밋</b>\n<pre>{result.stdout.strip()}</pre>")
    except Exception as e:
        send(chat_id, f"❌ git 조회 실패: {e}")


def cmd_db(chat_id: int, _args: str):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        lines = ["🗄️ <b>DB 테이블 통계</b>\n━━━━━━━━━━━━━━━━━━━━━━━━"]
        for (t,) in tables:
            try:
                cnt = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
                lines.append(f"  {t}: <b>{cnt}</b>행")
            except Exception:
                lines.append(f"  {t}: 조회실패")
        conn.close()
        send(chat_id, "\n".join(lines))
    except Exception as e:
        send(chat_id, f"❌ DB 조회 실패: {e}")


def cmd_apply_test(chat_id: int, _args: str):
    send(chat_id, (
        "🔗 <b>Apply 테스트 링크</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👉 https://bridge-chi-lime.vercel.app/apply\n\n"
        "Chrome에서 열어서 테스트 지원서를 제출해보세요.\n"
        "제출 후 관리자 페이지에서 확인:\n"
        "👉 https://bridge-chi-lime.vercel.app/admin"
    ))


def cmd_resume(chat_id: int, args: str):
    candidate_id = args.strip()
    if not candidate_id:
        send(chat_id, "❓ 후보자 ID를 입력하세요\n예: /resume 6147")
        return
    send(chat_id, f"⏳ 후보자 <b>{candidate_id}</b> 이력서 변환 시작...")
    try:
        result = subprocess.run(
            [PYTHON, "-X", "utf8",
             str(PROJECT_ROOT / "tools" / "resume_converter" / "pdf_builder.py"),
             "--candidate-id", candidate_id],
            capture_output=True, text=True, timeout=60,
            cwd=str(PROJECT_ROOT)
        )
        out = (result.stdout + result.stderr)[-2000:]
        send(chat_id, f"✅ 변환 완료\n<pre>{out}</pre>")
    except Exception as e:
        send(chat_id, f"❌ 변환 실패: {e}")


def cmd_run(chat_id: int, args: str):
    """간단한 안전 명령 실행 (read-only 계열만)"""
    SAFE_PREFIXES = ("git log", "git status", "git diff --stat", "dir ", "ls ",
                     "python", "echo", "type ", "cat ")
    cmd = args.strip()
    if not cmd:
        send(chat_id, "❓ 실행할 명령을 입력하세요\n예: /run git status")
        return
    safe = any(cmd.startswith(p) for p in SAFE_PREFIXES)
    if not safe:
        send(chat_id, f"🚫 보안 정책상 허용되지 않는 명령입니다: {cmd[:50]}")
        return
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=15, cwd=str(PROJECT_ROOT)
        )
        out = (result.stdout + result.stderr)[-2000:] or "(출력 없음)"
        send(chat_id, f"<pre>{out}</pre>")
    except Exception as e:
        send(chat_id, f"❌ 실패: {e}")


# ── deploy_gate IPC ───────────────────────────────────────────
def _write_gate_response(answer: str):
    """yes/no 응답을 파일에 기록 → deploy_gate.py가 읽음."""
    GATE_IPC_FILE.parent.mkdir(parents=True, exist_ok=True)
    GATE_IPC_FILE.write_text(
        json.dumps({"answer": answer, "ts": time.time()}),
        encoding="utf-8"
    )


# ── 자유 텍스트 의도 처리 ──────────────────────────────────────
_INTENT_KEYWORDS = {
    "rpa":      ["rpa", "크레이그", "craigslist", "게시", "포스팅", "올려"],
    "blog":     ["블로그", "blog", "claudeblog", "새글", "포스트"],
    "matjokdo": ["맛족도", "서이추", "서로이웃", "하트", "댓글"],
}

def _detect_simple_intent(text: str) -> str:
    t = text.lower()
    for intent, kws in _INTENT_KEYWORDS.items():
        if any(k in t for k in kws):
            return intent
    return "chat"


def _handle_free_text(chat_id: int, text: str):
    intent = _detect_simple_intent(text)

    if intent == "rpa":
        send(chat_id, "🚀 RPA 시작할게요...\n(계정 선택 창 없이 gray 계정 자동 실행)")
        _run_bg_reply(chat_id, [PYTHON, "-X", "utf8",
                                str(PROJECT_ROOT / "craigslist_auto_rpa.py"),
                                "--headless", "--account", "gray", "--limit", "5"])

    elif intent == "blog":
        blog_py = Path(r"Q:\Claudework\ClaudeBlog\.venv\Scripts\python.exe")
        blog_main = Path(r"Q:\Claudework\ClaudeBlog\main.py")
        py = str(blog_py) if blog_py.exists() else PYTHON
        send(chat_id, "📝 블로그 작업 시작...")
        _run_bg_reply(chat_id, [py, "-X", "utf8", str(blog_main), "--dry"],
                      cwd=str(blog_main.parent))

    elif intent == "matjokdo":
        mat_script = Path(r"Q:\Claudework\matjokdo_safe\main.py")
        if not mat_script.exists():
            send(chat_id, "❌ 맛족도 스크립트를 찾을 수 없어요")
            return
        send(chat_id, "🍽️ 맛족도 작업 시작...")
        _run_bg_reply(chat_id, [PYTHON, "-X", "utf8", str(mat_script)],
                      cwd=str(mat_script.parent))

    else:
        send(chat_id, (
            f"💬 받았습니다: <b>{text[:100]}</b>\n\n"
            "명령어 사용:\n"
            "/status /pipeline /watcher /git /db\n"
            "/resume [id] /help\n\n"
            "작업 지시 예:\n"
            "  'RPA 실행해줘' / '블로그 작업' / '맛족도'"
        ))


def _run_bg_reply(chat_id: int, cmd: list, cwd: str | None = None):
    """백그라운드 프로세스 실행 후 결과 전송."""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120,
            cwd=cwd or str(PROJECT_ROOT),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        out = (proc.stdout + proc.stderr)[-2000:].strip() or "(출력 없음)"
        rc = proc.returncode
        icon = "✅" if rc == 0 else "⚠️"
        send(chat_id, f"{icon} 완료 (rc={rc})\n<pre>{out}</pre>")
    except subprocess.TimeoutExpired:
        send(chat_id, "⏱ 타임아웃 (120초)")
    except Exception as e:
        send(chat_id, f"❌ 실행 오류: {e}")


COMMANDS = {
    "/help":       cmd_help,
    "/status":     cmd_status,
    "/pipeline":   cmd_pipeline,
    "/watcher":    cmd_watcher,
    "/git":        cmd_git,
    "/db":         cmd_db,
    "/apply_test": cmd_apply_test,
    "/resume":     cmd_resume,
    "/run":        cmd_run,
}


# ── 업데이트 처리 ──────────────────────────────────────────────
def handle_update(update: dict):
    # InlineKeyboard 버튼 콜백 처리 (deploy_gate 승인/취소 버튼)
    cb = update.get("callback_query")
    if cb:
        cb_id   = cb["id"]
        chat_id = cb["from"]["id"]
        data    = cb.get("data", "")
        # 스피너 제거
        tg_post("answerCallbackQuery", {"callback_query_id": cb_id})
        if chat_id not in get_subscribers():
            return
        if data == "gate_yes":
            _write_gate_response("yes")
            send(chat_id, "✅ 배포 승인됨")
        elif data == "gate_no":
            _write_gate_response("no")
            send(chat_id, "❌ 배포 취소됨")
        return

    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return

    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()

    # 구독자 외 차단
    if chat_id not in get_subscribers():
        return

    if not text:
        return

    print(f"[tg] 수신: chat_id={chat_id} text={text[:60]}")

    # ── deploy_gate yes/no IPC ──────────────────────────────
    lower = text.strip().lower()
    if lower in ("yes", "/yes", "y", "1", "✅", "✅ 승인", "승인"):
        _write_gate_response("yes")
        send(chat_id, "✅ 배포 승인됨")
        return
    if lower in ("no", "/no", "n", "0", "❌", "취소"):
        _write_gate_response("no")
        send(chat_id, "❌ 배포 취소됨")
        return

    # ── 커맨드 파싱 ────────────────────────────────────────
    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd_key = parts[0].split("@")[0].lower()  # /status@botname → /status
        args = parts[1] if len(parts) > 1 else ""
        handler = COMMANDS.get(cmd_key)
        if handler:
            handler(chat_id, args)
        else:
            send(chat_id, f"❓ 알 수 없는 명령: {cmd_key}\n/help 로 목록 확인")
        return

    # ── 자유 텍스트 → 의도 파악 ────────────────────────────
    _handle_free_text(chat_id, text)


# ── offset 관리 ──────────────────────────────────────────────
def load_offset() -> int:
    try:
        return int(offset_file.read_text().strip())
    except Exception:
        return 0


def save_offset(val: int):
    offset_file.parent.mkdir(parents=True, exist_ok=True)
    offset_file.write_text(str(val))


# ── 메인 루프 ──────────────────────────────────────────────
def main():
    print(f"[tg_commander] 시작 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    broadcast(
        "🟢 <b>BRIDGE Commander 시작</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "텔레그램에서 BRIDGE 작업을 대화형으로 진행합니다.\n\n"
        "주요 명령:\n"
        "  /status       — 전체 현황\n"
        "  /pipeline     — 파이프라인 큐\n"
        "  /watcher      — Watcher 상태\n"
        "  /resume [id]  — 이력서 변환\n"
        "  /git          — 최근 커밋\n"
        "  /db           — DB 통계\n"
        "  /apply_test   — Apply 테스트 링크\n"
        "  /help         — 전체 명령 목록\n\n"
        "지금 바로 명령을 입력해보세요 👇"
    )

    offset = load_offset()

    while True:
        try:
            resp = tg_get("getUpdates", {"offset": offset, "timeout": 30, "limit": 20})
            updates = resp.get("result", [])
            for upd in updates:
                uid = upd["update_id"]
                handle_update(upd)
                offset = uid + 1
                save_offset(offset)
        except KeyboardInterrupt:
            print("\n[tg_commander] 종료")
            break
        except Exception as e:
            print(f"[tg_commander] 루프 에러: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
