"""
BRIDGE Telegram Commander v2 -- 대화형 인터랙티브 봇
=====================================================
인라인 키보드 메뉴 + 상태 머신 기반 대화형 인터페이스.
실행: python tools/tg_commander.py
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
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
    print("[tg_commander] TELEGRAM_BOT_TOKEN 없음 -- 종료")
    sys.exit(1)

_PY_Q = PROJECT_ROOT.parent.parent / "Phtyon 3" / "python.exe"
PYTHON = str(_PY_Q) if _PY_Q.exists() else sys.executable
API_BASE = f"https://api.telegram.org/bot{TOKEN}"

offset_file   = PROJECT_ROOT / ".claude" / "tg_offset.txt"
GATE_IPC_FILE = PROJECT_ROOT / ".claude" / "tg_gate_response.json"


# -- 상태 머신 -----------------------------------------------------------------

@dataclass
class ChatState:
    state: str = "idle"
    data: dict = field(default_factory=dict)

_states: dict = {}

def get_state(chat_id):
    if chat_id not in _states:
        _states[chat_id] = ChatState()
    return _states[chat_id]

def set_state(chat_id, state, **data):
    s = get_state(chat_id)
    s.state = state
    s.data  = data

def clear_state(chat_id):
    _states[chat_id] = ChatState()


# -- Telegram API --------------------------------------------------------------

def tg_get(method, params=None):
    url = f"{API_BASE}/{method}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=35) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[tg] GET {method} 실패: {e}")
        return {}


def tg_post(method, data):
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
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


def send(chat_id, text, parse_mode="HTML", markup=None):
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for i, chunk in enumerate(chunks):
        body = {"chat_id": chat_id, "text": chunk, "parse_mode": parse_mode}
        if markup and i == len(chunks) - 1:
            body["reply_markup"] = markup
        tg_post("sendMessage", body)


def edit_msg(chat_id, message_id, text, markup=None, parse_mode="HTML"):
    body = {"chat_id": chat_id, "message_id": message_id,
            "text": text[:4000], "parse_mode": parse_mode}
    if markup:
        body["reply_markup"] = markup
    tg_post("editMessageText", body)


def answer_cb(cb_id, text=""):
    tg_post("answerCallbackQuery", {"callback_query_id": cb_id, "text": text})


def btn(text, data):
    return {"text": text, "callback_data": data}


def keyboard(*rows):
    return {"inline_keyboard": list(rows)}


# -- 구독자 --------------------------------------------------------------------

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


def broadcast(text, markup=None):
    for cid in get_subscribers():
        send(cid, text, markup=markup)


# -- 메인 메뉴 -----------------------------------------------------------------

MAIN_MENU_TEXT = (
    "BRIDGE Commander v2\n"
    "========================\n"
    "원하는 작업을 선택하세요."
)

MAIN_MENU_KB = keyboard(
    [btn("현황",    "status"),    btn("파이프라인", "pipeline")],
    [btn("RPA",     "rpa_menu"), btn("블로그",      "blog_start")],
    [btn("맛족도",  "mat_start"), btn("이력서 변환", "resume_start")],
    [btn("Git",     "git"),      btn("DB",           "db")],
    [btn("시스템",  "sys_menu")],
)


def show_main_menu(chat_id):
    clear_state(chat_id)
    send(chat_id, MAIN_MENU_TEXT, markup=MAIN_MENU_KB)


# -- 현황 ----------------------------------------------------------------------

def cb_status(chat_id, msg_id):
    lines = ["[현황] BRIDGE STATUS\n========================"]
    try:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.execute("SELECT COUNT(*) FROM candidates WHERE is_deleted=0").fetchone()[0]
        j = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_deleted=0").fetchone()[0]
        i = conn.execute("SELECT COUNT(*) FROM client_inquiries").fetchone()[0]
        conn.close()
        lines.append(f"후보: {c}명  |  공고: {j}건  |  문의: {i}건")
    except Exception as e:
        lines.append(f"DB 조회 실패: {e}")

    try:
        pdb = PROJECT_ROOT / "pipeline_queue.db"
        if pdb.exists():
            conn2 = sqlite3.connect(str(pdb))
            q = conn2.execute(
                "SELECT status, COUNT(*) FROM pipeline_queue GROUP BY status"
            ).fetchall()
            conn2.close()
            q_str = "  ".join(f"{s}:{n}" for s, n in q) if q else "비어있음"
            lines.append(f"파이프라인: {q_str}")
    except Exception:
        pass

    try:
        res = subprocess.run(
            ["powershell", "-Command",
             "(Get-ScheduledTask -TaskName 'BRIDGE_PipelineWatcher').State"],
            capture_output=True, text=True, timeout=5
        )
        lines.append(f"Watcher: {res.stdout.strip() or '확인불가'}")
    except Exception:
        pass

    try:
        res = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "log", "--oneline", "-1"],
            capture_output=True, text=True, timeout=5
        )
        lines.append(f"HEAD: {res.stdout.strip()}")
    except Exception:
        pass

    lines.append(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    kb = keyboard(
        [btn("새로고침", "status"), btn("파이프라인", "pipeline")],
        [btn("<- 메인",  "menu")],
    )
    edit_msg(chat_id, msg_id, "\n".join(lines), markup=kb)


# -- 파이프라인 ----------------------------------------------------------------

def cb_pipeline(chat_id, msg_id):
    pdb = PROJECT_ROOT / "pipeline_queue.db"
    if not pdb.exists():
        edit_msg(chat_id, msg_id, "pipeline_queue.db 없음",
                 markup=keyboard([btn("<- 메인", "menu")]))
        return
    try:
        conn = sqlite3.connect(str(pdb))
        rows = conn.execute(
            "SELECT id, filename, status, retry_count, created_at "
            "FROM pipeline_queue ORDER BY created_at DESC LIMIT 15"
        ).fetchall()
        conn.close()
    except Exception as e:
        edit_msg(chat_id, msg_id, f"조회 실패: {e}",
                 markup=keyboard([btn("<- 메인", "menu")]))
        return

    STATUS_ICON = {"queued": "[대기]", "running": "[실행]", "done": "[완료]",
                   "fail": "[실패]", "dlq": "[DLQ]"}
    lines = ["[파이프라인] 최근 15건\n========================"]
    if not rows:
        lines.append("비어있음")
    for r in rows:
        icon = STATUS_ICON.get(r[2], "[-]")
        lines.append(f"{icon} [{r[0]}] {r[1]}  retry:{r[3]}")

    edit_msg(chat_id, msg_id, "\n".join(lines),
             markup=keyboard([btn("새로고침", "pipeline"), btn("<- 메인", "menu")]))


# -- RPA 메뉴 ------------------------------------------------------------------

RPA_ACCOUNTS = ["gray", "brown", "blue", "black"]

def cb_rpa_menu(chat_id, msg_id):
    text = "[RPA] Craigslist\n========================\n계정을 선택하세요:"
    rows = [
        [btn(acc, f"rpa_acc_{acc}") for acc in RPA_ACCOUNTS[:2]],
        [btn(acc, f"rpa_acc_{acc}") for acc in RPA_ACCOUNTS[2:]],
        [btn("<- 메인", "menu")],
    ]
    edit_msg(chat_id, msg_id, text, markup={"inline_keyboard": rows})


def cb_rpa_acc(chat_id, msg_id, account):
    set_state(chat_id, "rpa_limit", account=account)
    text = f"[RPA] 계정: {account}\n========================\n게시 건수를 선택하세요:"
    kb = keyboard(
        [btn("1건", "rpa_run_1"), btn("3건", "rpa_run_3"),
         btn("5건", "rpa_run_5"), btn("10건", "rpa_run_10")],
        [btn("<- 계정선택", "rpa_menu")],
    )
    edit_msg(chat_id, msg_id, text, markup=kb)


def cb_rpa_run(chat_id, msg_id, limit):
    state   = get_state(chat_id)
    account = state.data.get("account", "gray")
    clear_state(chat_id)

    edit_msg(chat_id, msg_id,
             f"[RPA] 실행 중...\n계정: {account}  |  건수: {limit}건")

    cmd = [PYTHON, "-X", "utf8",
           str(PROJECT_ROOT / "craigslist_auto_rpa.py"),
           "--headless", "--account", account, "--limit", str(limit)]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=180, cwd=str(PROJECT_ROOT),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        out  = (proc.stdout + proc.stderr)[-2000:].strip() or "(출력 없음)"
        icon = "[완료]" if proc.returncode == 0 else "[경고]"
        result = f"{icon} RPA 완료 (rc={proc.returncode})\n{out}"
    except subprocess.TimeoutExpired:
        result = "[타임아웃] 180초 초과"
    except Exception as e:
        result = f"[오류] {e}"

    send(chat_id, result, markup=keyboard([btn("<- 메인", "menu")]))


# -- 블로그 --------------------------------------------------------------------

def cb_blog_start(chat_id, msg_id):
    edit_msg(chat_id, msg_id,
             "[블로그] ClaudeBlog\n========================\n모드를 선택하세요:",
             markup=keyboard(
                 [btn("테스트 (--dry)", "blog_dry"), btn("실제 발행 (--now)", "blog_now")],
                 [btn("<- 메인", "menu")],
             ))


def _run_blog(chat_id, flag):
    blog_py   = Path(r"Q:\Claudework\ClaudeBlog\.venv\Scripts\python.exe")
    blog_main = Path(r"Q:\Claudework\ClaudeBlog\main.py")
    py = str(blog_py) if blog_py.exists() else PYTHON
    send(chat_id, f"[블로그] 작업 시작 ({flag})...")
    try:
        proc = subprocess.run(
            [py, "-X", "utf8", str(blog_main), flag],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120, cwd=str(blog_main.parent),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        out  = (proc.stdout + proc.stderr)[-2000:].strip() or "(출력 없음)"
        icon = "[완료]" if proc.returncode == 0 else "[경고]"
        send(chat_id, f"{icon} {out}", markup=keyboard([btn("<- 메인", "menu")]))
    except subprocess.TimeoutExpired:
        send(chat_id, "[타임아웃]", markup=keyboard([btn("<- 메인", "menu")]))
    except Exception as e:
        send(chat_id, f"[오류] {e}", markup=keyboard([btn("<- 메인", "menu")]))


# -- 맛족도 --------------------------------------------------------------------

def cb_mat_start(chat_id, msg_id):
    mat = Path(r"Q:\Claudework\matjokdo_safe\main.py")
    if not mat.exists():
        edit_msg(chat_id, msg_id, "맛족도 스크립트 없음",
                 markup=keyboard([btn("<- 메인", "menu")]))
        return
    edit_msg(chat_id, msg_id,
             "[맛족도]\n========================\n실행하시겠습니까?",
             markup=keyboard(
                 [btn("실행", "mat_run"), btn("<- 메인", "menu")],
             ))


def cb_mat_run(chat_id, msg_id):
    edit_msg(chat_id, msg_id, "[맛족도] 실행 중...")
    mat = Path(r"Q:\Claudework\matjokdo_safe\main.py")
    try:
        proc = subprocess.run(
            [PYTHON, "-X", "utf8", str(mat)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120, cwd=str(mat.parent),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        out  = (proc.stdout + proc.stderr)[-2000:].strip() or "(출력 없음)"
        icon = "[완료]" if proc.returncode == 0 else "[경고]"
        send(chat_id, f"{icon} {out}", markup=keyboard([btn("<- 메인", "menu")]))
    except subprocess.TimeoutExpired:
        send(chat_id, "[타임아웃]", markup=keyboard([btn("<- 메인", "menu")]))
    except Exception as e:
        send(chat_id, f"[오류] {e}", markup=keyboard([btn("<- 메인", "menu")]))


# -- 이력서 변환 ---------------------------------------------------------------

def cb_resume_start(chat_id, msg_id):
    set_state(chat_id, "resume_input")
    edit_msg(chat_id, msg_id,
             "[이력서 변환]\n========================\n"
             "후보자 ID를 입력하세요:\n(예: 6147)",
             markup=keyboard([btn("취소", "menu")]))


def run_resume(chat_id, candidate_id):
    clear_state(chat_id)
    if not candidate_id.strip().isdigit():
        send(chat_id, "숫자 ID만 입력하세요.",
             markup=keyboard([btn("<- 메인", "menu")]))
        return
    send(chat_id, f"[이력서 변환] 후보자 {candidate_id} 처리 중...")
    try:
        proc = subprocess.run(
            [PYTHON, "-X", "utf8",
             str(PROJECT_ROOT / "tools" / "resume_converter" / "pdf_builder.py"),
             "--candidate-id", candidate_id.strip()],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120, cwd=str(PROJECT_ROOT),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        out  = (proc.stdout + proc.stderr)[-2000:].strip() or "(출력 없음)"
        icon = "[완료]" if proc.returncode == 0 else "[경고]"
        send(chat_id, f"{icon} {out}", markup=keyboard([btn("<- 메인", "menu")]))
    except subprocess.TimeoutExpired:
        send(chat_id, "[타임아웃]", markup=keyboard([btn("<- 메인", "menu")]))
    except Exception as e:
        send(chat_id, f"[오류] {e}", markup=keyboard([btn("<- 메인", "menu")]))


# -- Git -----------------------------------------------------------------------

def cb_git(chat_id, msg_id):
    try:
        res = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "log", "--oneline", "-8"],
            capture_output=True, text=True, timeout=5
        )
        text = f"[Git] 최근 커밋\n{res.stdout.strip()}"
    except Exception as e:
        text = f"git 실패: {e}"
    edit_msg(chat_id, msg_id, text,
             markup=keyboard([btn("새로고침", "git"), btn("<- 메인", "menu")]))


# -- DB ------------------------------------------------------------------------

def cb_db(chat_id, msg_id):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        lines = ["[DB] 테이블 통계\n========================"]
        for (t,) in tables:
            try:
                cnt = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
                lines.append(f"  {t}: {cnt}행")
            except Exception:
                lines.append(f"  {t}: 조회실패")
        conn.close()
        text = "\n".join(lines)
    except Exception as e:
        text = f"DB 조회 실패: {e}"
    edit_msg(chat_id, msg_id, text,
             markup=keyboard([btn("새로고침", "db"), btn("<- 메인", "menu")]))


# -- 시스템 메뉴 ---------------------------------------------------------------

def cb_sys_menu(chat_id, msg_id):
    kb = keyboard(
        [btn("Watcher 상태", "watcher"), btn("Task Scheduler", "tasks")],
        [btn("명령 실행",    "run_start")],
        [btn("<- 메인",       "menu")],
    )
    edit_msg(chat_id, msg_id, "[시스템]\n========================", markup=kb)


def cb_watcher(chat_id, msg_id):
    try:
        res = subprocess.run(
            ["powershell", "-Command",
             "Get-ScheduledTask -TaskName 'BRIDGE_PipelineWatcher' "
             "| Select-Object TaskName,State,LastRunTime | ConvertTo-Json"],
            capture_output=True, text=True, timeout=8
        )
        d    = json.loads(res.stdout)
        text = (f"[Watcher]\n"
                f"상태: {d.get('State','?')}\n"
                f"마지막 실행: {d.get('LastRunTime','?')}")
    except Exception as e:
        text = f"Watcher 조회 실패: {e}"
    edit_msg(chat_id, msg_id, text,
             markup=keyboard([btn("새로고침", "watcher"), btn("<- 시스템", "sys_menu")]))


def cb_tasks(chat_id, msg_id):
    names = ["BRIDGE_TgCommander", "BRIDGE_PipelineWatcher", "BRIDGE_AdOnlyRefresh"]
    lines = ["[Task Scheduler]\n========================"]
    for name in names:
        try:
            res = subprocess.run(
                ["powershell", "-Command",
                 f"(Get-ScheduledTask -TaskName '{name}' -ErrorAction SilentlyContinue).State"],
                capture_output=True, text=True, timeout=5
            )
            state = res.stdout.strip() or "없음"
            lines.append(f"  {name}: {state}")
        except Exception:
            lines.append(f"  {name}: 확인불가")
    edit_msg(chat_id, msg_id, "\n".join(lines),
             markup=keyboard([btn("새로고침", "tasks"), btn("<- 시스템", "sys_menu")]))


def cb_run_start(chat_id, msg_id):
    set_state(chat_id, "run_input")
    edit_msg(chat_id, msg_id,
             "[명령 실행]\n========================\n"
             "실행할 명령어를 입력하세요:\n"
             "(허용: git log/status/diff, dir, ls, echo, python)",
             markup=keyboard([btn("취소", "sys_menu")]))


SAFE_PREFIXES = ("git log", "git status", "git diff", "git branch",
                 "dir ", "ls ", "python", "echo", "type ", "cat ")

def run_cmd(chat_id, cmd):
    clear_state(chat_id)
    parts = cmd.strip().split()
    if not parts or not any(cmd.strip().startswith(p) for p in SAFE_PREFIXES):
        send(chat_id, f"허용되지 않는 명령: {cmd[:60]}",
             markup=keyboard([btn("<- 시스템", "sys_menu")]))
        return
    try:
        res = subprocess.run(  # nosec B603 -- allowlist-validated before exec
            parts, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15,
            cwd=str(PROJECT_ROOT)
        )
        out = (res.stdout + res.stderr)[-2000:].strip() or "(출력 없음)"
        send(chat_id, out, markup=keyboard([btn("<- 시스템", "sys_menu")]))
    except subprocess.TimeoutExpired:
        send(chat_id, "[타임아웃]", markup=keyboard([btn("<- 시스템", "sys_menu")]))
    except Exception as e:
        send(chat_id, f"[오류] {e}", markup=keyboard([btn("<- 시스템", "sys_menu")]))


# -- deploy gate IPC -----------------------------------------------------------

def write_gate_response(answer):
    GATE_IPC_FILE.parent.mkdir(parents=True, exist_ok=True)
    GATE_IPC_FILE.write_text(
        json.dumps({"answer": answer, "ts": time.time()}),
        encoding="utf-8"
    )


# -- 콜백 라우터 ---------------------------------------------------------------

def route_callback(chat_id, cb_id, data, msg_id):
    answer_cb(cb_id)

    if data == "menu":
        edit_msg(chat_id, msg_id, MAIN_MENU_TEXT, markup=MAIN_MENU_KB)
        clear_state(chat_id)
    elif data == "status":   cb_status(chat_id, msg_id)
    elif data == "pipeline": cb_pipeline(chat_id, msg_id)
    elif data == "git":      cb_git(chat_id, msg_id)
    elif data == "db":       cb_db(chat_id, msg_id)
    elif data == "rpa_menu":          cb_rpa_menu(chat_id, msg_id)
    elif data.startswith("rpa_acc_"): cb_rpa_acc(chat_id, msg_id, data[8:])
    elif data.startswith("rpa_run_"): cb_rpa_run(chat_id, msg_id, int(data[8:]))
    elif data == "blog_start": cb_blog_start(chat_id, msg_id)
    elif data == "blog_dry":   _run_blog(chat_id, "--dry")
    elif data == "blog_now":   _run_blog(chat_id, "--now")
    elif data == "mat_start": cb_mat_start(chat_id, msg_id)
    elif data == "mat_run":   cb_mat_run(chat_id, msg_id)
    elif data == "resume_start": cb_resume_start(chat_id, msg_id)
    elif data == "sys_menu": cb_sys_menu(chat_id, msg_id)
    elif data == "watcher":  cb_watcher(chat_id, msg_id)
    elif data == "tasks":    cb_tasks(chat_id, msg_id)
    elif data == "run_start":cb_run_start(chat_id, msg_id)
    elif data == "gate_yes":
        write_gate_response("yes")
        send(chat_id, "[배포 승인됨]")
    elif data == "gate_no":
        write_gate_response("no")
        send(chat_id, "[배포 취소됨]")
    else:
        answer_cb(cb_id, f"알 수 없는 액션: {data}")


# -- 텍스트 메시지 처리 --------------------------------------------------------

def handle_text(chat_id, text):
    st = get_state(chat_id)

    if st.state == "resume_input":
        run_resume(chat_id, text.strip())
        return

    if st.state == "run_input":
        run_cmd(chat_id, text.strip())
        return

    lower = text.strip().lower()

    if lower in ("yes", "/yes", "y", "1", "승인"):
        write_gate_response("yes")
        send(chat_id, "[배포 승인됨]", markup=keyboard([btn("<- 메인", "menu")]))
        return
    if lower in ("no", "/no", "n", "0", "취소"):
        write_gate_response("no")
        send(chat_id, "[배포 취소됨]", markup=keyboard([btn("<- 메인", "menu")]))
        return

    if lower in ("/start", "/help", "/menu", "메뉴", "menu"):
        show_main_menu(chat_id)
        return

    _LEGACY = {
        "/status": "status", "/pipeline": "pipeline", "/git": "git",
        "/db": "db", "/watcher": "watcher",
    }
    cmd_key = lower.split()[0].split("@")[0]
    if cmd_key in _LEGACY:
        _handle_legacy_as_new_msg(chat_id, _LEGACY[cmd_key])
        return

    show_main_menu(chat_id)


def _handle_legacy_as_new_msg(chat_id, action):
    res = tg_post("sendMessage", {"chat_id": chat_id, "text": "처리 중..."})
    msg_id = res.get("result", {}).get("message_id")
    if not msg_id:
        return
    dispatch = {
        "status":   cb_status,
        "pipeline": cb_pipeline,
        "git":      cb_git,
        "db":       cb_db,
        "watcher":  cb_watcher,
    }
    if action in dispatch:
        dispatch[action](chat_id, msg_id)


# -- 업데이트 처리 -------------------------------------------------------------

def handle_update(update):
    subs = get_subscribers()

    cb = update.get("callback_query")
    if cb:
        chat_id = cb["from"]["id"]
        if chat_id not in subs:
            return
        route_callback(
            chat_id,
            cb_id  = cb["id"],
            data   = cb.get("data", ""),
            msg_id = cb.get("message", {}).get("message_id", 0),
        )
        return

    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return
    chat_id = msg["chat"]["id"]
    if chat_id not in subs:
        return
    text = msg.get("text", "").strip()
    if not text:
        return

    print(f"[tg] 수신: chat_id={chat_id} text={text[:60]}")
    handle_text(chat_id, text)


# -- offset 관리 ---------------------------------------------------------------

def load_offset():
    try:
        return int(offset_file.read_text().strip())
    except Exception:
        return 0


def save_offset(val):
    offset_file.parent.mkdir(parents=True, exist_ok=True)
    offset_file.write_text(str(val))


# -- 메인 루프 -----------------------------------------------------------------

def main():
    print(f"[tg_commander v2] 시작 -- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    broadcast(
        "BRIDGE Commander v2 시작\n"
        "========================\n"
        "버튼 메뉴로 BRIDGE 작업을 제어하세요.\n"
        "/start 또는 아무 메시지 -> 메인 메뉴",
        markup=MAIN_MENU_KB,
    )

    offset = load_offset()
    while True:
        try:
            resp = tg_get("getUpdates", {"offset": offset, "timeout": 30, "limit": 20})
            for upd in resp.get("result", []):
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
