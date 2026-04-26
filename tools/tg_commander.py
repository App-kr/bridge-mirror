"""
BRIDGE Telegram Commander v2 -- 대화형 인터랙티브 봇
=====================================================
인라인 키보드 메뉴 + 상태 머신 기반 대화형 인터페이스.
실행: python tools/tg_commander.py
"""

import json
import os
import queue
import re
import sqlite3
import subprocess
import sys
import threading
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
_LOG_PATH     = PROJECT_ROOT / "logs" / "tg_commander.log"
_START_TIME   = time.time()


def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        _LOG_PATH.parent.mkdir(exist_ok=True)
        with open(str(_LOG_PATH), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


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
    except urllib.error.HTTPError as e:
        body = {}
        try:
            body = json.loads(e.read())
        except Exception:
            pass
        body["error_code"] = e.code
        if e.code != 409:
            print(f"[tg] GET {method} HTTP {e.code}")
        return body
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
    except urllib.error.HTTPError as e:
        body = {"ok": False}
        try:
            body.update(json.loads(e.read()))
        except Exception:
            pass
        if method not in ("answerCallbackQuery",):
            _log(f"[tg] POST {method} HTTP {e.code}: {body.get('description','')[:120]}")
        return body
    except Exception as e:
        _log(f"[tg] POST {method} 실패: {e}")
        return {}


def send(chat_id, text, parse_mode="HTML", markup=None):
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for i, chunk in enumerate(chunks):
        body = {"chat_id": chat_id, "text": chunk, "parse_mode": parse_mode}
        if markup and i == len(chunks) - 1:
            body["reply_markup"] = markup
        tg_post("sendMessage", body)


def edit_msg(chat_id, message_id, text, markup=None, parse_mode="HTML"):
    if not message_id:
        send(chat_id, text, markup=markup, parse_mode=parse_mode)
        return
    body = {"chat_id": chat_id, "message_id": message_id,
            "text": text[:4000], "parse_mode": parse_mode}
    if markup:
        body["reply_markup"] = markup
    r = tg_post("editMessageText", body)
    if not r.get("ok"):
        # edit 실패(메시지 오래됨 등) → 새 메시지로 폴백
        send(chat_id, text, markup=markup, parse_mode=parse_mode)


def answer_cb(cb_id, text=""):
    tg_post("answerCallbackQuery", {"callback_query_id": cb_id, "text": text})


def btn(text, data):
    return {"text": text, "callback_data": data}


def keyboard(*rows):
    return {"inline_keyboard": list(rows)}


# -- 구독자 --------------------------------------------------------------------

_subscribers_cache: list = []
_subscribers_ts: float = 0.0
_SUBS_TTL = 60.0  # 60초마다 갱신


def get_subscribers() -> list:
    global _subscribers_cache, _subscribers_ts
    now = time.time()
    if now - _subscribers_ts < _SUBS_TTL and _subscribers_cache:
        return _subscribers_cache
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=3)
        rows = conn.execute(
            "SELECT chat_id FROM tg_alert_subscribers WHERE active=1"
        ).fetchall()
        conn.close()
        _subscribers_cache = [r[0] for r in rows]
        _subscribers_ts = now
    except Exception as e:
        print(f"[tg] get_subscribers 실패 (캐시 사용): {e}")
    return _subscribers_cache


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
    _log(f"[cb] chat={chat_id} data={data} msg={msg_id}")
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
    elif data.startswith("term_reply_"):
        # ask_user 버튼 → 텍스트 입력 모드로 전환
        tid = data[len("term_reply_"):]
        set_state(chat_id, f"term_ask_{tid}", tid=tid)
        edit_msg(chat_id, msg_id,
                 f"[T{tid}] 에이전트 질문에 답변을 입력하세요:",
                 markup=keyboard([btn("취소", "menu")]))
    else:
        answer_cb(cb_id, f"알 수 없는 액션: {data}")


# -- 직접 키워드 실행 (LLM 없이 즉시 처리) ------------------------------------

_RPA_DIRECT_RE  = re.compile(r'(?:rpa|광고|크레이그|craig)\s*(\d+)\s*건', re.IGNORECASE)
# 숫자 없는 RPA 직접 실행 키워드 (기본 5건, gray 계정)
_RPA_NOW_KEYS   = ("rpa 실행", "rpa 돌려", "rpa 돌려줘", "rpa해", "rpa 해줘", "rpa 해",
                   "광고 올려", "광고 올려줘", "광고 실행", "광고 돌려", "광고 돌려줘",
                   "크레이그 올려", "크레이그 실행", "크레이그 돌려",
                   "craig 실행", "craig 올려", "크레이그리스트 실행")
# 댓글 답방 (matjokdo main.py --run)
_DAEBANG_KEYS   = ("블로그 작업 시작", "블로그 작업시작", "답방 시작", "답방시작", "댓글 답방",
                   "댓글답방", "블로그 답방", "댓글 확인", "댓글확인", "답방 해", "답방해줘",
                   "블로그 댓글", "댓글 달린거 확인", "댓글달린거")
# 블로그 포스팅 (ClaudeBlog main.py --now)
_BLOG_NOW_KEYS  = ("블로그 포스팅 시작", "블로그 포스팅", "블로그 발행", "새 글 발행", "블로그 글 써", "블로그 올려", "블로그 새글")
_BLOG_DRY_KEYS  = ("블로그 테스트", "블로그 드라이", "블로그 dry", "blog dry")
_NEW_APP_KEYS   = ("신규접수확인", "신규 접수확인", "신규접수 확인", "새 접수", "신규 후보", "새 후보", "신규접수")
_MAIL_STAT_KEYS = ("자동메일 몇건", "메일답장 몇건", "자동 메일 몇건", "메일 몇건", "자동답장 몇건", "메일답장 오늘")


def _run_daebang(chat_id):
    """matjokdo main.py --run : 댓글 확인 + 답방 실제 실행."""
    mat = Path(r"Q:\Claudework\matjokdo_safe\main.py")
    if not mat.exists():
        send(chat_id, "[답방] 스크립트 없음: matjokdo_safe/main.py",
             markup=keyboard([btn("메인 메뉴", "menu")]))
        return
    send(chat_id, "[답방] 댓글 확인 + 답방 작업 시작...\n(완료까지 수 분 소요)")
    try:
        proc = subprocess.run(
            [PYTHON, "-X", "utf8", str(mat), "--run"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=600, cwd=str(mat.parent),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        out  = (proc.stdout + proc.stderr)[-2000:].strip() or "(출력 없음)"
        icon = "[완료]" if proc.returncode == 0 else "[경고]"
        send(chat_id, f"{icon} 답방 완료\n{out}", markup=keyboard([btn("메인 메뉴", "menu")]))
    except subprocess.TimeoutExpired:
        send(chat_id, "[타임아웃] 600초 초과", markup=keyboard([btn("메인 메뉴", "menu")]))
    except Exception as e:
        send(chat_id, f"[오류] {e}", markup=keyboard([btn("메인 메뉴", "menu")]))


def _quick_bridge_new(chat_id):
    """브릿지 신규 접수 현황 DB 직접 조회."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur  = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")

        cur.execute(
            "SELECT COUNT(*) FROM candidates WHERE DATE(created_at)=? AND (is_deleted IS NULL OR is_deleted=0)",
            (today,)
        )
        cand_today = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM candidates WHERE DATE(created_at)>=date('now','-7 days') AND (is_deleted IS NULL OR is_deleted=0)"
        )
        cand_week = cur.fetchone()[0]

        try:
            cur.execute("SELECT COUNT(*) FROM client_inquiries WHERE DATE(created_at)=?", (today,))
            inq_today = cur.fetchone()[0]
        except Exception:
            inq_today = 0

        # 가장 최근 후보자 3명
        cur.execute(
            "SELECT sheet_number, full_name, nationality, created_at FROM candidates "
            "WHERE (is_deleted IS NULL OR is_deleted=0) ORDER BY id DESC LIMIT 3"
        )
        recent = cur.fetchall()
        conn.close()

        lines = [
            "[브릿지 신규접수 현황]",
            f"오늘 신규 후보자: {cand_today}명",
            f"이번 주 신규 후보자: {cand_week}명",
            f"오늘 신규 문의: {inq_today}건",
        ]
        if recent:
            lines.append("\n최근 후보자:")
            for row in recent:
                sn, name, nat, cat = row
                cat_str = cat[:10] if cat else "?"
                # name은 암호화된 경우 가림 처리
                name_disp = f"#{sn}" if (name and (name.startswith("T3v1") or len(name) > 60)) else (name or f"#{sn}")
                lines.append(f"  {name_disp} / {nat or '?'} / {cat_str}")

        send(chat_id, "\n".join(lines), markup=keyboard([btn("메인 메뉴", "menu")]))
    except Exception as e:
        send(chat_id, f"[오류] DB 조회 실패: {e}", markup=keyboard([btn("메인 메뉴", "menu")]))


def _quick_mail_stats(chat_id):
    """자동메일 발송 통계 DB 직접 조회."""
    try:
        conn  = sqlite3.connect(str(DB_PATH))
        cur   = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")

        today_count = total_count = 0
        week_count  = 0
        try:
            cur.execute("SELECT COUNT(*) FROM mail_introduce_log WHERE DATE(sent_at)=?", (today,))
            today_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM mail_introduce_log WHERE DATE(sent_at)>=date('now','-7 days')")
            week_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM mail_introduce_log")
            total_count = cur.fetchone()[0]
        except Exception:
            pass

        conn.close()
        msg = (
            f"[자동메일 발송 통계]\n"
            f"오늘 발송: {today_count}건\n"
            f"이번 주: {week_count}건\n"
            f"총 누적: {total_count}건"
        )
        send(chat_id, msg, markup=keyboard([btn("메인 메뉴", "menu")]))
    except Exception as e:
        send(chat_id, f"[오류] DB 조회 실패: {e}", markup=keyboard([btn("메인 메뉴", "menu")]))


def _try_direct_cmd(chat_id, text: str) -> bool:
    """한국어 키워드 직접 매칭 → LLM 없이 즉시 실행. 처리되면 True 반환."""
    t  = text.strip()
    tl = t.lower()

    # 블로그 댓글 답방 (matjokdo --run)
    if any(k in tl for k in _DAEBANG_KEYS):
        threading.Thread(target=_run_daebang, args=(chat_id,), daemon=True).start()
        return True

    # 블로그 포스팅 발행 (ClaudeBlog --now)
    if any(k in tl for k in _BLOG_NOW_KEYS):
        send(chat_id, "[블로그] 실제 발행 시작...")
        threading.Thread(target=_run_blog, args=(chat_id, "--now"), daemon=True).start()
        return True

    # 블로그 테스트
    if any(k in tl for k in _BLOG_DRY_KEYS):
        send(chat_id, "[블로그] 테스트 모드 시작...")
        threading.Thread(target=_run_blog, args=(chat_id, "--dry"), daemon=True).start()
        return True

    # RPA 광고 N건 (예: "광고 20건 해", "RPA 10건")
    m = _RPA_DIRECT_RE.search(t)
    if m:
        limit = max(1, min(int(m.group(1)), 50))
        threading.Thread(target=_run_rpa_direct, args=(chat_id, "gray", limit), daemon=True).start()
        return True

    # RPA 숫자 없는 직접 실행 키워드 (기본 5건)
    if any(k in tl for k in _RPA_NOW_KEYS):
        send(chat_id, "[RPA] gray 계정으로 5건 실행 중...")
        threading.Thread(target=_run_rpa_direct, args=(chat_id, "gray", 5), daemon=True).start()
        return True

    # 브릿지 신규접수 확인
    if any(k in tl for k in _NEW_APP_KEYS):
        _quick_bridge_new(chat_id)
        return True
    if "신규" in tl and ("확인" in tl or "접수" in tl):
        _quick_bridge_new(chat_id)
        return True
    if "홈페이지" in tl and ("신규" in tl or "접수" in tl):
        _quick_bridge_new(chat_id)
        return True
    if "브릿지" in tl and ("신규" in tl or "접수" in tl or "확인" in tl):
        _quick_bridge_new(chat_id)
        return True

    # 자동메일 답장 통계
    if any(k in tl for k in _MAIL_STAT_KEYS):
        _quick_mail_stats(chat_id)
        return True
    if "자동" in tl and "메일" in tl and ("몇" in tl or "통계" in tl or "얼마" in tl or "오늘" in tl):
        _quick_mail_stats(chat_id)
        return True
    if "메일답장" in tl and ("오늘" in tl or "몇" in tl):
        _quick_mail_stats(chat_id)
        return True

    return False


# -- 텍스트 메시지 처리 --------------------------------------------------------

_TERM_TARGET_RE = re.compile(r"^[Tt](\d+)[:：]\s*(.+)$", re.DOTALL)

def handle_text(chat_id, text):
    st = get_state(chat_id)

    # ── [1] ask_user 대기 중인 터미널 답변 처리 ───────────────
    awaiting = _find_awaiting_ask(chat_id)
    if awaiting:
        awaiting.reply_ask(text.strip())
        send(chat_id, f"[T{awaiting.tid}] 답변 전달됨.")
        return

    # ── [2] term_ask_* 상태 (버튼으로 열린 답장 모드) ─────────
    if st.state.startswith("term_ask_"):
        tid = st.data.get("tid", "1")
        clear_state(chat_id)
        key = _terminal_key(chat_id, tid)
        with _t_lock:
            t = _terminals.get(key)
        if t and t.status == "running":
            t.reply_ask(text.strip())
            send(chat_id, f"[T{tid}] 답변 전달됨.")
        else:
            send(chat_id, f"[T{tid}] 터미널이 없거나 종료됨.")
        return

    # ── [3] 특정 터미널 지정 주입 "T1: 메시지" ────────────────
    m = _TERM_TARGET_RE.match(text.strip())
    if m:
        tid_target, msg_body = m.group(1), m.group(2)
        key = _terminal_key(chat_id, tid_target)
        with _t_lock:
            t = _terminals.get(key)
        if t and t.status == "running":
            t.inject_message(msg_body.strip())
            send(chat_id, f"[T{tid_target}] 메시지 전달됨.")
            return

    # ── [4] 실행 중 터미널에 자동 주입 (stop 키워드 처리 포함) ─
    running = _find_running_terminal(chat_id)
    lower_t = text.strip().lower()
    if running and lower_t in ("stop", "중지", "멈춰", "cancel", "스탑"):
        _stop_terminal(chat_id, running.tid)
        return
    if running and not text.strip().startswith("/"):
        running.inject_message(text.strip())
        send(chat_id, f"[T{running.tid}] 메시지 전달됨. ('/menu' 입력 시 메인 메뉴)")
        return

    # ── 기존 처리 ────────────────────────────────────────────
    if st.state == "resume_input":
        run_resume(chat_id, text.strip())
        return

    if st.state == "run_input":
        run_cmd(chat_id, text.strip())
        return

    lower = lower_t

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

    if lower in ("/ping", "ping", "핑"):
        uptime = int(time.time() - _START_TIME)
        send(chat_id, f"[pong] 봇 살아있음\nuptime={uptime}s\npid={os.getpid()}",
             markup=keyboard([btn("메인 메뉴", "menu")]))
        return

    _LEGACY = {
        "/status": "status", "/pipeline": "pipeline", "/git": "git",
        "/db": "db", "/watcher": "watcher",
    }
    cmd_key = lower.split()[0].split("@")[0]
    if cmd_key in _LEGACY:
        _handle_legacy_as_new_msg(chat_id, _LEGACY[cmd_key])
        return

    # ── 직접 키워드 매칭 (LLM 없이 즉시 실행) ────────────────────
    if _try_direct_cmd(chat_id, text):
        return

    # 자연어 대화 → Claude Haiku
    _ask_claude(chat_id, text)


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


# -- 대화형 Claude 처리 --------------------------------------------------------

_conv_history: dict = {}   # {chat_id: [{"role": ..., "content": ...}, ...]}
_MAX_HIST = 10

_SYSTEM = """\
당신은 BRIDGE 텔레그램 봇입니다. 구인 플랫폼 운영자 Scarlett과 한국어로 대화합니다.
짧고 친근하게 답하세요. 이모지 금지.

[중요 원칙 — 반드시 지킬 것]
1. 사용자 메시지에 아래 [액션 트리거 키워드]가 명시적으로 있을 때만 action 선택.
2. 키워드가 없으면 무조건 action=null (단순 대화).
3. 절대 임의로 action="cancel" 선택 금지. "취소", "멈춰", "stop", "그만"이 있을 때만.
4. 모호하면 action=null + 질문하는 reply.

[액션 트리거 키워드 사전 — 이 단어들이 메시지에 있을 때만 해당 action]
- status     : "현황", "상태", "status"
- pipeline   : "파이프라인", "큐", "queue"
- git        : "커밋", "git"
- db         : "DB", "디비", "통계"
- watcher    : "watcher", "워처"
- rpa        : "RPA", "광고", "Craigslist", "크레이그"
- blog_dry   : "블로그 테스트", "blog dry"
- blog_now   : "블로그 발행", "블로그 올려"
- daebang    : "답방", "댓글 답방", "블로그 댓글"
- matjokdo   : "맛족도"
- resume     : "이력서 변환"
- restore    : "복원", "백업 목록"
- bridge_new : "신규 접수", "신규 후보자", "신규 문의"
- mail_stats : "메일 통계", "자동메일", "메일 몇건"
- cancel     : "취소", "멈춰", "그만", "stop"
- terminal   : "터미널", "에이전트 시작", "agent"
- terminal_stop  : "터미널 멈춰", "터미널 중지", "terminal stop"
- terminal_status: "터미널 현황", "터미널 상태"

[응답 형식] JSON만 출력. 마크다운 코드블록 금지. 다른 텍스트 금지.
{"action": "액션명 또는 null", "params": {}, "reply": "자연어 답변"}

[예시]
사용자: "안녕"
응답: {"action": null, "params": {}, "reply": "안녕하세요. 무엇을 도와드릴까요?"}

사용자: "밀린 작업해"
응답: {"action": null, "params": {}, "reply": "어떤 작업 말씀이세요? RPA, 블로그 답방, 신규 접수 확인 등 구체적으로 알려주세요."}

사용자: "현황 알려줘"
응답: {"action": "status", "params": {}, "reply": "BRIDGE 현황 확인할게요."}

사용자: "취소해"
응답: {"action": "cancel", "params": {}, "reply": "알겠어요, 취소했어요."}

사용자: "RPA 광고 20건"
응답: {"action": "rpa", "params": {"account": "gray", "limit": 20}, "reply": "RPA 광고 20건 실행할게요."}

사용자: "터미널 1에서 bridge base 분석"
응답: {"action": "terminal", "params": {"tid": "1", "task": "bridge base 분석", "workdir": "Q:/Claudework/bridge base"}, "reply": "터미널 1에서 분석 시작."}

사용자: "댓글 답방해"
응답: {"action": "daebang", "params": {}, "reply": "댓글 확인 + 답방 시작할게요."}

사용자: "신규 접수 확인"
응답: {"action": "bridge_new", "params": {}, "reply": "신규 접수 현황 확인할게요."}
"""


def _hist_add(chat_id, role, content):
    h = _conv_history.setdefault(chat_id, [])
    h.append({"role": role, "content": content})
    if len(h) > _MAX_HIST * 2:
        _conv_history[chat_id] = h[-(_MAX_HIST * 2):]


def _ollama_works() -> bool:
    """Ollama 로컬 서버 동작 확인."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


# Ollama 우선순위: 큰 모델일수록 명령 이해도 ↑
_OLLAMA_PREFERENCE = [
    "qwen2.5:14b", "qwen2.5:7b", "llama3.1:8b",
    "qwen2.5:3b", "llama3.2:3b",
]
_ollama_model_cache: dict = {"name": None, "ts": 0.0}


def _best_ollama_model() -> str:
    """현재 설치된 Ollama 모델 중 가장 큰(정확한) 것 반환. 5분 캐시."""
    now = time.time()
    if _ollama_model_cache["name"] and now - _ollama_model_cache["ts"] < 300:
        return _ollama_model_cache["name"]
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as r:
            data = json.loads(r.read())
        installed = {m["name"] for m in data.get("models", [])}
        for cand in _OLLAMA_PREFERENCE:
            if cand in installed:
                _ollama_model_cache.update({"name": cand, "ts": now})
                _log(f"[ollama] using model: {cand}")
                return cand
        # 설치된 첫 번째라도 사용
        if installed:
            first = sorted(installed)[0]
            _ollama_model_cache.update({"name": first, "ts": now})
            return first
    except Exception as e:
        _log(f"[ollama] _best_ollama_model err: {e}")
    return "qwen2.5:3b"


def _anthropic_key_works(k: str) -> bool:
    """Anthropic 키 유효성 빠른 확인 (timeout=5s)."""
    try:
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps({
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 5,
                "messages": [{"role": "user", "content": "hi"}],
            }).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": k,
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def _gemini_key_works(k: str) -> bool:
    """Gemini 키 유효성 빠른 확인 (timeout=5s)."""
    try:
        payload = {"contents": [{"role": "user", "parts": [{"text": "hi"}]}],
                   "generationConfig": {"maxOutputTokens": 5}}
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"gemini-2.0-flash:generateContent?key={k}")
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


# 키 검증 결과 캐시 (provider → (works, ts))
_key_cache: dict = {}
_KEY_CACHE_TTL = 300.0   # 5분


def _cached_check(name: str, fn, *args) -> bool:
    """키 검증 결과 캐싱 (5분)."""
    now = time.time()
    cached = _key_cache.get(name)
    if cached and now - cached[1] < _KEY_CACHE_TTL:
        return cached[0]
    ok = fn(*args)
    _key_cache[name] = (ok, now)
    return ok


def _get_llm_key(prefer: str = "auto"):
    """사용 가능한 LLM 반환. (provider, key_or_None) 튜플.

    prefer="conversation": Ollama 우선 (빠름, 무료, 로컬)
    prefer="agent": Anthropic → Gemini → Ollama (도구사용 강력순)
    prefer="auto" (default): conversation과 동일
    """
    candidates = []

    # 1. Anthropic
    try:
        ak = bx_read("ANTHROPIC_API_KEY")
        if ak and ak.startswith("sk-ant-"):
            if _cached_check("anthropic:" + ak[:20], _anthropic_key_works, ak):
                candidates.append(("anthropic", ak))
    except Exception:
        pass

    # 2. GOOGLE_API_KEY
    try:
        gk = bx_read("GOOGLE_API_KEY")
        if gk and gk.startswith("AIza"):
            if _cached_check("gemini:" + gk[:20], _gemini_key_works, gk):
                candidates.append(("gemini", gk))
    except Exception:
        pass

    # 3. GEMINI_KEYS_JSON
    try:
        from bx import get_gemini_keys
        for entry in get_gemini_keys():
            gk = entry.get("key", "")
            if gk and gk.startswith("AIza"):
                if _cached_check("gemini:" + gk[:20], _gemini_key_works, gk):
                    candidates.append(("gemini", gk))
    except Exception:
        pass

    # 4. Ollama (항상 시도)
    if _cached_check("ollama", _ollama_works):
        candidates.append(("ollama", None))

    if not candidates:
        return (None, None)

    # 우선순위 적용
    if prefer == "agent":
        order = ["anthropic", "gemini", "ollama"]
    else:
        order = ["ollama", "anthropic", "gemini"]
    candidates.sort(key=lambda c: order.index(c[0]) if c[0] in order else 99)
    return candidates[0]


def _list_llm_keys(prefer: str = "auto"):
    """폴백용 — 사용 가능한 모든 (provider, key) 리스트 반환."""
    seen = set()
    out = []

    # 모든 후보 수집
    pool = []
    try:
        ak = bx_read("ANTHROPIC_API_KEY")
        if ak and ak.startswith("sk-ant-"):
            # prefer="agent" 모드: 검증 없이 직접 추가 (타임아웃 이슈 방지)
            if prefer == "agent":
                pool.append(("anthropic", ak))
            elif _cached_check("anthropic:" + ak[:20], _anthropic_key_works, ak):
                pool.append(("anthropic", ak))
    except Exception:
        pass
    try:
        gk = bx_read("GOOGLE_API_KEY")
        if gk and gk.startswith("AIza"):
            if _cached_check("gemini:" + gk[:20], _gemini_key_works, gk):
                pool.append(("gemini", gk))
    except Exception:
        pass
    try:
        from bx import get_gemini_keys
        for entry in get_gemini_keys():
            gk = entry.get("key", "")
            if gk and gk.startswith("AIza"):
                if _cached_check("gemini:" + gk[:20], _gemini_key_works, gk):
                    pool.append(("gemini", gk))
    except Exception:
        pass
    if _cached_check("ollama", _ollama_works):
        pool.append(("ollama", None))

    if prefer == "agent":
        order = ["anthropic", "gemini", "ollama"]
    else:
        order = ["ollama", "anthropic", "gemini"]
    pool.sort(key=lambda c: order.index(c[0]) if c[0] in order else 99)

    for prov, key in pool:
        ident = (prov, key[:20] if key else "")
        if ident in seen:
            continue
        seen.add(ident)
        out.append((prov, key))
    return out


def _call_llm(provider, api_key, prompt, history):
    """provider에 따라 LLM API 호출. 텍스트 반환."""
    if provider == "anthropic":
        payload = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 400,
            "system": _SYSTEM,
            "messages": history,
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(req, timeout=25) as r:
            resp = json.loads(r.read())
        return resp["content"][0]["text"].strip()

    elif provider == "gemini":
        turns = []
        for m in history:
            role = "user" if m["role"] == "user" else "model"
            turns.append({"role": role, "parts": [{"text": m["content"]}]})
        if turns and turns[0]["role"] == "user":
            turns[0]["parts"][0]["text"] = _SYSTEM + "\n\n" + turns[0]["parts"][0]["text"]
        payload = {"contents": turns, "generationConfig": {"maxOutputTokens": 400}}
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"gemini-2.0-flash:generateContent?key={api_key}")
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=25) as r:
            resp = json.loads(r.read())
        return resp["candidates"][0]["content"]["parts"][0]["text"].strip()

    elif provider == "ollama":
        # Ollama 로컬 무료 모델 — 설치된 최선 선택 (qwen2.5:7b > 3b 등)
        ollama_model = _best_ollama_model()
        msgs = [{"role": "system", "content": _SYSTEM}]
        for m in history:
            msgs.append({"role": m["role"], "content": m["content"]})
        payload = {
            "model": ollama_model,
            "messages": msgs,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2, "num_predict": 400},
        }
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
        return resp.get("message", {}).get("content", "").strip()

    raise ValueError(f"unknown provider: {provider}")


def _parse_llm_json(raw: str) -> dict:
    """LLM 응답에서 JSON 추출."""
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _deterministic_route(text: str) -> dict | None:
    """LLM 부르기 전 결정론적 키워드 매칭. 작은 모델이 멍청해도 이건 정확함.
    매칭되면 {action, params, reply} 반환, 안 되면 None."""
    t = text.strip().lower()
    # 취소/중단 — 가장 위험하니 먼저
    for kw in ("취소", "그만", "멈춰", "하지마", "stop", "cancel"):
        if kw in t:
            # "터미널 X 멈춰" 는 terminal_stop으로 가야 함
            if "터미널" in t or "terminal" in t:
                m = re.search(r"(?:터미널|terminal)\s*(\d+)", t)
                tid = m.group(1) if m else "1"
                return {"action": "terminal_stop", "params": {"tid": tid},
                        "reply": f"터미널 {tid} 중지할게요."}
            return {"action": "cancel", "params": {}, "reply": "알겠어요, 취소했어요."}

    # 터미널 명령
    if "터미널" in t or "terminal" in t:
        # 현황
        if "현황" in t or "상태" in t or "status" in t:
            return {"action": "terminal_status", "params": {}, "reply": "터미널 현황 확인할게요."}
        # 새 작업: "터미널 1에서 ..." 또는 "터미널 1 ..." 형식
        m = re.search(r"(?:터미널|terminal)\s*(\d+)\s*(?:에서|에)?\s*(.+)", text, re.IGNORECASE)
        if m:
            tid = m.group(1)
            task = m.group(2).strip()
            if task and len(task) > 3:
                return {"action": "terminal", "params": {"tid": tid, "task": task},
                        "reply": f"터미널 {tid}에서 시작할게요."}

    # 팀 회의 — "팀회의 윷놀이" / "팀에서 ... 만들어" / "팀 토론 ..."
    if ("팀회의" in t or "팀 회의" in t or "팀토론" in t or "팀 토론" in t
        or "팀 의논" in t or "팀의논" in t or "team council" in t):
        # task: 키워드 뒤 본문
        m = re.search(r"(?:팀\s*(?:회의|토론|의논)|team\s*council)\s*[:은는을를에서]?\s*(.+)",
                      text, re.IGNORECASE)
        task = (m.group(1).strip() if m else text.strip())
        if not task or len(task) < 3:
            task = text.strip()
        return {"action": "team", "params": {"task": task},
                "reply": f"팀 회의 시작 — 과업: {task[:80]}\n6개 팀 (Architect/Designer/Backend/Security/Payment/QA) 자율 토론 → SPEC.md 까지 자동 생성."}

    # RPA — "RPA 광고 N건/개/번/회/포스팅/포스트" 패턴
    if "rpa" in t or "광고" in t or "craigslist" in t or "크레이그" in t or "포스팅" in t:
        # 숫자 + (건|개|번|회|포스팅|포스트|건수) — 어떤 단위든 매칭
        m = re.search(r"(\d+)\s*(?:건|개|번|회|포스팅|포스트|건수|times|posts)", text, re.IGNORECASE)
        if not m:
            # 순수 숫자만 나와도 매칭 (예: "rpa 20")
            m = re.search(r"(?:rpa|광고|포스팅)\D*(\d+)", text, re.IGNORECASE)
        limit = int(m.group(1)) if m else 5
        limit = max(1, min(limit, 100))  # 안전 범위
        # 계정 추론: 사용자가 명시했으면 사용
        account = "gray"
        for a in ("gray", "green", "brown", "purple", "account1", "account2", "account3", "account4"):
            if a in t:
                account = a
                break
        return {"action": "rpa", "params": {"account": account, "limit": limit},
                "reply": f"RPA 포스팅 {limit}건 ({account}) 실행 — 동일직업 자동 제외."}

    # 단일 키워드 매칭
    SIMPLE = [
        (("현황", "상태"),                           "status",     "BRIDGE 현황 확인할게요."),
        (("파이프라인", "큐", "queue"),              "pipeline",   "파이프라인 큐 확인."),
        (("커밋", "git log"),                       "git",        "최근 커밋 확인."),
        (("디비 통계", "db 통계", "db통계"),         "db",         "DB 통계 확인."),
        (("watcher", "워처", "워치독"),              "watcher",    "Watcher 상태 확인."),
        (("블로그 테스트", "블로그테스트"),          "blog_dry",   "블로그 테스트 시작."),
        (("블로그 발행", "블로그 올려"),             "blog_now",   "블로그 발행."),
        (("답방", "댓글 답방", "블로그 댓글"),       "daebang",    "댓글 확인 + 답방 시작."),
        (("맛족도",),                                "matjokdo",   "맛족도 실행."),
        (("이력서 변환",),                           "resume",     "이력서 변환."),
        (("백업 목록", "백업목록", "복원"),          "restore",    "백업 목록 확인."),
        (("신규 접수", "신규접수", "신규 후보자"),   "bridge_new", "신규 접수 확인."),
        (("자동메일", "메일 통계", "메일통계", "메일 몇건"), "mail_stats", "자동메일 통계 확인."),
    ]
    for kws, action, reply in SIMPLE:
        if any(kw in t for kw in kws):
            return {"action": action, "params": {}, "reply": reply}

    return None


def _ask_claude(chat_id, user_text):
    """LLM(Anthropic → Gemini → Ollama) 호출 → 의도 파악 + 실행. 모든 백엔드 실패 시에만 에러 표시.

    먼저 결정론적 키워드 매칭 시도 → 매칭되면 LLM 건너뛰고 즉시 실행 (작은 Ollama 모델 보호)."""
    # 1) 결정론적 라우팅 — 명백한 명령어는 LLM 건너뛰기
    det = _deterministic_route(user_text)
    if det:
        _log(f"[det] action={det['action']} for {user_text[:50]!r}")
        _hist_add(chat_id, "user", user_text)
        _hist_add(chat_id, "assistant", det.get("reply", ""))
        _dispatch_action(chat_id, det.get("action", ""), det.get("params", {}),
                         det.get("reply", ""), provider=None, api_key=None)
        return

    # 2) LLM 폴백
    candidates = _list_llm_keys(prefer="agent")

    if not candidates:
        send(chat_id, "AI 백엔드 모두 다운(키 무효+Ollama 불가). 버튼 메뉴를 사용하세요.",
             markup=keyboard([btn("메인 메뉴", "menu")]))
        return

    _hist_add(chat_id, "user", user_text)

    raw = None
    last_err = None
    used_provider, used_key = None, None
    for prov, key in candidates:
        try:
            raw = _call_llm(prov, key, user_text, _conv_history[chat_id][:])
            used_provider, used_key = prov, key
            _log(f"[llm] OK provider={prov}")
            break
        except Exception as e:
            last_err = f"{prov}: {str(e)[:120]}"
            _log(f"[llm] FAIL {prov}: {str(e)[:120]}")
            continue

    if raw is None:
        send(chat_id, f"AI 모든 백엔드 실패: {last_err}\n\n메뉴를 사용하세요.",
             markup=keyboard([btn("메인 메뉴", "menu")]))
        return

    try:
        parsed = _parse_llm_json(raw)
    except Exception as e:
        # JSON 파싱 실패 → 그냥 raw 텍스트를 답변으로
        parsed = {"action": "", "params": {}, "reply": raw[:1500]}

    provider, api_key = used_provider, used_key

    action = (parsed.get("action") or "").strip()
    params = parsed.get("params") or {}
    reply  = parsed.get("reply", "")

    # ── 안전장치: 작은 모델(qwen2.5:3b 등)이 키워드 없는데 임의로 action 선택하는 것 차단 ──
    # 사용자 메시지에 해당 action의 키워드가 실제로 있는지 검증
    _ACTION_KEYWORDS = {
        "cancel":          ["취소", "멈춰", "그만", "stop", "cancel", "하지마"],
        "status":          ["현황", "상태", "status"],
        "pipeline":        ["파이프라인", "큐", "queue", "pipeline"],
        "git":             ["커밋", "git"],
        "db":              ["DB", "디비", "통계", "데이터베이스"],
        "watcher":         ["watcher", "워처", "워치독", "watchdog"],
        "rpa":             ["RPA", "광고", "Craigslist", "크레이그", "포스팅", "게시"],
        "blog_dry":        ["블로그 테스트", "블로그테스트", "blog dry", "dry"],
        "blog_now":        ["블로그 발행", "블로그발행", "블로그 올려", "블로그 작성"],
        "daebang":         ["답방", "댓글"],
        "matjokdo":        ["맛족도"],
        "resume":          ["이력서"],
        "restore":         ["복원", "백업"],
        "bridge_new":      ["신규", "접수", "새로", "오늘", "이번주"],
        "mail_stats":      ["메일", "발송", "자동메일"],
        "terminal":        ["터미널", "terminal", "에이전트", "agent"],
        "terminal_stop":   ["터미널", "terminal", "에이전트"],
        "terminal_status": ["터미널", "terminal", "에이전트"],
    }
    if action and action != "null":
        kws = _ACTION_KEYWORDS.get(action, [])
        text_lower = user_text.lower()
        if kws and not any(kw.lower() in text_lower for kw in kws):
            _log(f"[guard] action={action} dropped — no keyword in user_text={user_text[:50]!r}")
            # 키워드 없이 action 선택 → 안전하게 null로 강제
            action = ""
            if not reply or len(reply) < 5:
                reply = "어떤 작업 말씀이세요? 구체적으로 알려주세요. (예: RPA 광고 10건, 블로그 답방, 신규 접수 확인)"

    _hist_add(chat_id, "assistant", reply)
    _dispatch_action(chat_id, action, params, reply, provider, api_key)


def _dispatch_action(chat_id, action: str, params: dict, reply: str,
                     provider: str | None, api_key: str | None):
    """액션 분기 (deterministic/LLM 양쪽에서 사용)."""
    if action == "cancel":
        clear_state(chat_id)
        send(chat_id, reply, markup=keyboard([btn("메인 메뉴", "menu")]))
        return

    if action == "restore":
        _do_restore_list(chat_id, reply)
        return

    if action == "bridge_new":
        send(chat_id, reply)
        _quick_bridge_new(chat_id)
        return

    if action == "mail_stats":
        send(chat_id, reply)
        _quick_mail_stats(chat_id)
        return

    if action in ("status", "pipeline", "git", "db", "watcher"):
        send(chat_id, reply)
        _handle_legacy_as_new_msg(chat_id, action)
        return

    if action == "rpa":
        account = params.get("account", "gray")
        limit   = int(params.get("limit", 5))
        send(chat_id, reply)
        _run_rpa_direct(chat_id, account, limit)
        return

    if action == "daebang":
        send(chat_id, reply)
        threading.Thread(target=_run_daebang, args=(chat_id,), daemon=True).start()
        return

    if action == "blog_dry":
        send(chat_id, reply)
        _run_blog(chat_id, "--dry")
        return

    if action == "blog_now":
        send(chat_id, reply)
        _run_blog(chat_id, "--now")
        return

    if action == "matjokdo":
        send(chat_id, reply)
        mat = Path(r"Q:\Claudework\matjokdo_safe\main.py")
        if not mat.exists():
            send(chat_id, "맛족도 스크립트 없음.", markup=keyboard([btn("메인 메뉴", "menu")]))
        else:
            def _run_mat():
                try:
                    proc = subprocess.run(
                        [PYTHON, "-X", "utf8", str(mat)],
                        capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=120, cwd=str(mat.parent),
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    out = (proc.stdout + proc.stderr)[-2000:].strip() or "(출력 없음)"
                    icon = "[완료]" if proc.returncode == 0 else "[경고]"
                    send(chat_id, f"{icon} {out}", markup=keyboard([btn("메인 메뉴", "menu")]))
                except Exception as e:
                    send(chat_id, f"[오류] {e}", markup=keyboard([btn("메인 메뉴", "menu")]))
            threading.Thread(target=_run_mat, daemon=True).start()
        return

    if action == "resume":
        # params 키 호환: candidate_id / id / cid
        cid_raw = params.get("candidate_id") or params.get("id") or params.get("cid") or ""
        cid = str(cid_raw).strip()
        if cid.isdigit():
            send(chat_id, reply)
            run_resume(chat_id, cid)
        else:
            set_state(chat_id, "resume_input")
            send(chat_id, reply + "\n후보자 ID를 숫자로 입력해주세요:")
        return

    if action == "terminal":
        tid     = str(params.get("tid", "1"))
        task    = params.get("task", "").strip()
        workdir = params.get("workdir") or None
        if not task:
            send(chat_id, "어떤 작업을 할까요?")
        else:
            send(chat_id, reply)
            # provider/key 없으면 agent용 키 자동 선택 (deterministic 경로)
            if not provider or provider == "ollama":
                cands = _list_llm_keys(prefer="agent")
                if cands:
                    provider, api_key = cands[0]
            _launch_terminal(chat_id, tid, task, provider or "ollama",
                             api_key, workdir)
        return

    if action == "terminal_stop":
        tid = str(params.get("tid", "1"))
        send(chat_id, reply)
        _stop_terminal(chat_id, tid)
        return

    if action == "terminal_status":
        send(chat_id, reply)
        _terminal_status_all(chat_id)
        return

    if action == "team":
        task_str = params.get("task", "").strip() or "(empty)"
        send(chat_id, reply)
        _run_team_council(chat_id, task_str)
        return

    # null or unknown → 대화 답변만
    send(chat_id, reply, markup=keyboard([btn("메인 메뉴", "menu")]))


def _run_team_council(chat_id, task_str: str):
    """6팀 자율 토론 → SPEC.md 생성. 백그라운드 스레드 (5~15분 소요)."""
    send(chat_id, f"[팀회의 시작] {task_str[:120]}\n예상 5~15분. 매 팀 발언마다 즉시 보고합니다.")

    def _worker():
        try:
            sys.path.insert(0, str(Path(r"Q:/Claudework/agentic_os")))
            from agents.team_council import run_council, save_council_result

            # 팀 발언이 나올 때마다 텔레그램에 실시간 보고
            def _cb(role, msg):
                try:
                    send(chat_id, f"[{role}]\n{msg[:1500]}")
                except Exception:
                    pass

            result = run_council(task_str, callback=_cb, parallel=True)
            base = save_council_result(result)
            spec = result["spec"]
            send(chat_id,
                 f"[회의 완료] {result['duration_sec']}초 소요\n\n"
                 f"--- SPEC.md (요약) ---\n{spec[:2500]}",
                 markup=keyboard([btn("메인 메뉴", "menu")]))
            send(chat_id, f"전체 토론 + SPEC 저장: {base}.SPEC.md")
            _log(f"[council] done task={task_str[:60]} dur={result['duration_sec']}s")
        except Exception as e:
            send(chat_id, f"[회의 오류] {e}", markup=keyboard([btn("메인 메뉴", "menu")]))
            _log(f"[council] ERR: {e}")

    threading.Thread(target=_worker, daemon=True).start()


def _run_rpa_direct(chat_id, account, limit):
    """RPA 실행을 백그라운드 스레드로 — 봇 폴링 차단 방지."""
    send(chat_id, f"[RPA 실행 중] 계정: {account} | {limit}건 — 완료까지 최대 10분")

    def _rpa_worker():
        cmd = [PYTHON, "-X", "utf8",
               str(PROJECT_ROOT / "craigslist_auto_rpa.py"),
               "--headless", "--account", account, "--limit", str(limit)]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=600, cwd=str(PROJECT_ROOT),
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            out  = (proc.stdout + proc.stderr)[-2000:].strip() or "(출력 없음)"
            icon = "[완료]" if proc.returncode == 0 else "[경고]"
            send(chat_id, f"{icon} RPA {limit}건 ({account})\n{out}",
                 markup=keyboard([btn("메인 메뉴", "menu")]))
            _log(f"[rpa] done account={account} limit={limit} rc={proc.returncode}")
        except subprocess.TimeoutExpired:
            send(chat_id, "[타임아웃] 10분 초과 — RPA 강제 종료",
                 markup=keyboard([btn("메인 메뉴", "menu")]))
            _log(f"[rpa] TIMEOUT account={account} limit={limit}")
        except Exception as e:
            send(chat_id, f"[오류] {e}", markup=keyboard([btn("메인 메뉴", "menu")]))
            _log(f"[rpa] ERR account={account} limit={limit}: {e}")

    threading.Thread(target=_rpa_worker, daemon=True).start()


def _do_restore_list(chat_id, reply):
    """최근 백업 목록 표시."""
    backup_dir = PROJECT_ROOT / "backups"
    if not backup_dir.exists():
        send(chat_id, "백업 폴더가 없어요.", markup=keyboard([btn("메인 메뉴", "menu")]))
        return
    backups = sorted(
        (p for p in backup_dir.iterdir() if p.is_dir() or p.suffix in (".zip", ".tar", ".db")),
        key=lambda p: p.stat().st_mtime, reverse=True
    )[:6]
    if not backups:
        send(chat_id, "백업 파일이 없어요.", markup=keyboard([btn("메인 메뉴", "menu")]))
        return
    lines = [reply, "", "최근 백업:"]
    for b in backups:
        mtime = datetime.fromtimestamp(b.stat().st_mtime).strftime("%m/%d %H:%M")
        lines.append(f"  {mtime}  {b.name}")
    send(chat_id, "\n".join(lines), markup=keyboard([btn("메인 메뉴", "menu")]))


# ═══════════════════════════════════════════════════════════════════════════════
# 에이전트 터미널 — Claude Sonnet + tool_use 기반 자율 실행
# ═══════════════════════════════════════════════════════════════════════════════

_AGENT_TOOLS = [
    {
        "name": "bash",
        "description": "셸 명령 실행. 파일 생성·수정·조회·패키지 설치·빌드 등.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "실행할 명령어"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "파일 내용 읽기.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "파일 경로"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "파일 생성/덮어쓰기.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path":    {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_files",
        "description": "디렉토리 목록 조회.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "경로 (기본: 현재)"}},
            "required": [],
        },
    },
    {
        "name": "ask_user",
        "description": "작업 중 사용자에게 질문하고 답변을 받는다. 방향 결정이 꼭 필요할 때만 사용.",
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string", "description": "사용자에게 할 질문"}},
            "required": ["question"],
        },
    },
    {
        "name": "search_files",
        "description": "디렉토리에서 텍스트 패턴 검색 (grep). 코드 탐색, 함수 위치 확인에 사용.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "검색 패턴 (정규식 가능)"},
                "path":    {"type": "string", "description": "검색 경로 (기본: workdir)"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "git",
        "description": "Git 명령 실행. status/diff/log/add/commit/branch/show/stash 허용.",
        "input_schema": {
            "type": "object",
            "properties": {"args": {"type": "string", "description": "예: 'add tools/foo.py' / 'commit -m 메시지'"}},
            "required": ["args"],
        },
    },
    {
        "name": "sub_task",
        "description": "독립적인 서브태스크를 다른 터미널 ID에 위임하고 결과를 받는다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tid":     {"type": "string", "description": "서브 터미널 ID (예: '2')"},
                "task":    {"type": "string", "description": "서브태스크 내용"},
                "workdir": {"type": "string", "description": "작업 디렉토리 (선택)"},
            },
            "required": ["tid", "task"],
        },
    },
]

_AGENT_SYS = """\
당신은 BRIDGE 서버의 자율 개발/실행 에이전트입니다.
운영자 Scarlett의 지시를 받아 실제 작업을 완수하세요.

규칙:
- 도구를 적극적으로 사용해 직접 파일을 만들고, 코드를 작성하고, 명령을 실행하세요.
- 각 단계 완료 후 간략히 진행 상황을 설명하는 텍스트를 함께 출력하세요 (한국어, 1~2줄).
- 마지막에 완료 요약을 출력하세요.
- 보안: rm -rf /, DROP TABLE, git push --force 금지.
- 작업 디렉토리 외부 쓰기 금지.
- ask_user: 반드시 필요한 결정만. 빈번한 질문 금지.
- sub_task: 독립적으로 실행 가능한 단위만 위임. 순환 호출 금지.
- search_files: 코드 탐색 시 bash grep 대신 사용 권장.
- git: add/commit 전 반드시 status와 diff로 변경사항 확인.
- 사용자가 실행 중 메시지를 보내면 [사용자 개입] 태그로 전달됨. 즉시 반영.
"""

_BLOCKED_BASH = re.compile(
    r"(rm\s+-rf\s+/|DROP\s+TABLE|git\s+push\s+--force|format\s+[a-z]:)",
    re.IGNORECASE,
)

# {f"{chat_id}_{tid}": AgentTerminal}
_terminals: dict = {}
_t_lock = threading.Lock()


class AgentTerminal:
    MAX_STEPS = 40   # 무한루프 방지

    def __init__(self, tid: str, chat_id: int, task: str,
                 provider: str, api_key: str, workdir: str | None = None,
                 parent_tid: str | None = None):
        self.tid        = tid
        self.chat_id    = chat_id
        self.task       = task
        self.provider   = provider
        self.api_key    = api_key
        self.workdir    = workdir or str(PROJECT_ROOT)
        self.parent_tid = parent_tid          # 순환 sub_task 방지
        self.status     = "running"
        self.messages: list = []
        self._stop      = False
        self._thread    = threading.Thread(target=self._run, daemon=True)
        # ── 대화형 개입 ─────────────────────────────────
        self._inbox     = queue.Queue()       # 사용자 → 에이전트 메시지 주입
        self._is_asking = False               # ask_user 대기 중 플래그
        self._ask_event = threading.Event()   # ask_user 응답 신호
        self._ask_reply = ""                  # ask_user 답변 저장
        self._ask_lock  = threading.Lock()
        # ── PATH 환경변수 ────────────────────────────────
        self.env        = self._build_env()

    @staticmethod
    def _build_env() -> dict:
        """Q:\\Phtyon 3 를 PATH 앞에 추가한 환경변수 딕셔너리."""
        e = os.environ.copy()
        py_dir = str(Path(r"Q:\Phtyon 3"))
        paths = e.get("PATH", "").split(os.pathsep)
        if py_dir not in paths:
            paths.insert(0, py_dir)
        e["PATH"] = os.pathsep.join(paths)
        return e

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop = True
        self.status = "stopped"
        # ask_user 대기 중이면 깨워서 종료
        with self._ask_lock:
            self._ask_reply = "[중단됨]"
            self._ask_event.set()

    # ── 외부 API (inject_message / reply_ask) ─────────────
    def inject_message(self, text: str):
        """실행 중 사용자가 보낸 텍스트를 inbox에 넣는다."""
        self._inbox.put(text)

    def reply_ask(self, text: str):
        """ask_user 대기 중인 에이전트에 답변 전달."""
        with self._ask_lock:
            self._ask_reply = text
            self._ask_event.set()

    # ── 내부 ──────────────────────────────────────────────────
    def _tag(self, text: str) -> str:
        return f"[T{self.tid}] {text}"

    def _send(self, text: str, markup=None):
        send(self.chat_id, self._tag(text)[:4000], markup=markup)

    def _run(self):
        try:
            self._loop()
        except Exception as e:
            self.status = "error"
            self._send(f"에이전트 오류: {e}")

    def _drain_inbox(self):
        """inbox 메시지를 꺼내 에이전트 messages에 주입."""
        msgs = []
        while True:
            try:
                msgs.append(self._inbox.get_nowait())
            except queue.Empty:
                break
        if msgs:
            combined = "\n".join(f"[사용자 개입] {m}" for m in msgs)
            self.messages.append({"role": "user", "content": combined})
            self._send(f"사용자 메시지 반영: {combined[:200]}")

    def _loop(self):
        self.messages = [{"role": "user", "content": self.task}]
        self._send(f"시작: {self.task[:80]}")
        step = 0

        while not self._stop and step < self.MAX_STEPS:
            self._drain_inbox()   # 매 스텝 전 inbox 확인
            step += 1
            resp = self._call_api()
            if not resp:
                break

            stop_reason = resp.get("stop_reason", "")
            content     = resp.get("content", [])
            self.messages.append({"role": "assistant", "content": content})

            # 텍스트 출력
            texts = [b["text"] for b in content if b.get("type") == "text" and b.get("text","").strip()]
            if texts:
                self._send("\n".join(texts))

            if stop_reason == "end_turn":
                self.status = "done"
                self._send("완료.", markup=keyboard([btn("메인 메뉴", "menu")]))
                break

            if stop_reason == "tool_use":
                tool_blocks = [b for b in content if b.get("type") == "tool_use"]
                results = []
                for tb in tool_blocks:
                    result_text = self._exec_tool(tb["name"], tb.get("input", {}))
                    results.append({
                        "type":        "tool_result",
                        "tool_use_id": tb["id"],
                        "content":     result_text[:8000],
                    })
                self.messages.append({"role": "user", "content": results})
            else:
                break

        if step >= self.MAX_STEPS:
            self._send(f"최대 스텝({self.MAX_STEPS}) 도달, 중단.")
            self.status = "done"

    def _call_api(self) -> dict | None:
        """현재 provider 시도 → 실패 시 다른 provider로 폴백 (agent: anthropic > gemini > ollama)."""
        # 매 호출마다 최신 가용 백엔드 목록 — 키 만료/할당량 변동 대응
        candidates = _list_llm_keys(prefer="agent")
        # 현재 self.provider를 우선
        ordered = [(self.provider, self.api_key)]
        for prov, key in candidates:
            if (prov, key) not in ordered:
                ordered.append((prov, key))

        last_err = None
        for prov, key in ordered:
            try:
                self.provider = prov
                self.api_key  = key
                if prov == "anthropic":
                    return self._call_anthropic()
                if prov == "gemini":
                    return self._call_gemini()
                if prov == "ollama":
                    return self._call_ollama()
            except Exception as e:
                last_err = f"{prov}: {str(e)[:120]}"
                _log(f"[agent T{self.tid}] {prov} fail: {str(e)[:120]}")
                continue
        self._send(f"API 모든 백엔드 실패: {last_err}")
        return None

    def _call_anthropic(self) -> dict:
        payload = {
            "model":      "claude-sonnet-4-6",
            "max_tokens": 4096,
            "system":     _AGENT_SYS,
            "tools":      _AGENT_TOOLS,
            "messages":   self.messages,
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type":      "application/json",
                "x-api-key":         self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())

    def _call_gemini(self) -> dict:
        """Gemini function calling → Anthropic 형식으로 정규화."""
        # Gemini tool 선언 변환
        fn_decls = []
        for t in _AGENT_TOOLS:
            fn_decls.append({
                "name":        t["name"],
                "description": t["description"],
                "parameters":  t["input_schema"],
            })

        # messages → Gemini contents 변환
        contents = []
        for m in self.messages:
            if isinstance(m["content"], str):
                contents.append({"role": "user" if m["role"] == "user" else "model",
                                  "parts": [{"text": m["content"]}]})
            elif isinstance(m["content"], list):
                # tool_result 형식
                parts = []
                for block in m["content"]:
                    if block.get("type") == "tool_result":
                        parts.append({"functionResponse": {
                            "name":     block.get("tool_use_id", "tool"),
                            "response": {"output": block.get("content", "")},
                        }})
                    elif block.get("type") == "tool_use":
                        parts.append({"functionCall": {
                            "name": block["name"],
                            "args": block.get("input", {}),
                        }})
                    elif block.get("type") == "text":
                        parts.append({"text": block.get("text", "")})
                if parts:
                    contents.append({"role": "user" if m["role"] == "user" else "model",
                                      "parts": parts})

        # system을 첫 user 메시지에 prefix
        if contents and contents[0]["role"] == "user":
            first_text = contents[0]["parts"][0].get("text", "")
            contents[0]["parts"][0]["text"] = _AGENT_SYS + "\n\n" + first_text

        payload = {
            "contents": contents,
            "tools": [{"functionDeclarations": fn_decls}],
            "generationConfig": {"maxOutputTokens": 4096},
        }
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"gemini-2.0-flash:generateContent?key={self.api_key}")
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = json.loads(r.read())

        # Gemini 응답 → Anthropic 형식으로 정규화
        candidate = raw["candidates"][0]
        parts     = candidate["content"]["parts"]
        finish    = candidate.get("finishReason", "STOP")

        content_blocks = []
        has_fn = False
        for p in parts:
            if "text" in p and p["text"].strip():
                content_blocks.append({"type": "text", "text": p["text"]})
            if "functionCall" in p:
                has_fn = True
                fc = p["functionCall"]
                content_blocks.append({
                    "type":  "tool_use",
                    "id":    f"call_{fc['name']}_{int(time.time())}",
                    "name":  fc["name"],
                    "input": fc.get("args", {}),
                })

        return {
            "stop_reason": "tool_use" if has_fn else "end_turn",
            "content":     content_blocks,
        }

    def _call_ollama(self) -> dict:
        """Ollama qwen2.5:3b function calling → Anthropic 형식으로 정규화."""
        # Ollama tools 선언 (OpenAI 형식)
        tools = []
        for t in _AGENT_TOOLS:
            tools.append({
                "type": "function",
                "function": {
                    "name":        t["name"],
                    "description": t["description"],
                    "parameters":  t["input_schema"],
                },
            })

        # messages → Ollama chat 형식
        msgs = [{"role": "system", "content": _AGENT_SYS}]
        for m in self.messages:
            if isinstance(m["content"], str):
                msgs.append({"role": m["role"], "content": m["content"]})
            elif isinstance(m["content"], list):
                # tool_use / tool_result 블록 변환
                if m["role"] == "assistant":
                    text_parts = []
                    tool_calls = []
                    for block in m["content"]:
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_use":
                            tool_calls.append({
                                "id":   block.get("id", ""),
                                "type": "function",
                                "function": {
                                    "name":      block["name"],
                                    "arguments": block.get("input", {}),
                                },
                            })
                    a_msg = {"role": "assistant", "content": "\n".join(text_parts)}
                    if tool_calls:
                        a_msg["tool_calls"] = tool_calls
                    msgs.append(a_msg)
                else:
                    # user role with tool_result blocks
                    for block in m["content"]:
                        if block.get("type") == "tool_result":
                            msgs.append({
                                "role":         "tool",
                                "content":      block.get("content", ""),
                                "tool_call_id": block.get("tool_use_id", ""),
                            })
                        elif block.get("type") == "text":
                            msgs.append({"role": "user", "content": block.get("text", "")})

        payload = {
            "model":    _best_ollama_model(),
            "messages": msgs,
            "tools":    tools,
            "stream":   False,
            "options":  {"temperature": 0.2, "num_predict": 1024},
        }
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = json.loads(r.read())

        msg = raw.get("message", {})
        text = (msg.get("content") or "").strip()
        tool_calls = msg.get("tool_calls") or []

        content_blocks = []
        if text:
            content_blocks.append({"type": "text", "text": text})
        has_tool = False
        for tc in tool_calls:
            fn = tc.get("function", {})
            args = fn.get("arguments", {})
            # Ollama는 args를 dict 또는 str로 줌
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {"_raw": args}
            has_tool = True
            content_blocks.append({
                "type":  "tool_use",
                "id":    tc.get("id") or f"call_{fn.get('name','tool')}_{int(time.time()*1000)}",
                "name":  fn.get("name", ""),
                "input": args,
            })

        return {
            "stop_reason": "tool_use" if has_tool else "end_turn",
            "content":     content_blocks,
        }

    def _exec_tool(self, name: str, inp: dict) -> str:
        if name == "bash":
            return self._bash(inp.get("command", ""))
        if name == "read_file":
            return self._read(inp.get("path", ""))
        if name == "write_file":
            return self._write(inp.get("path", ""), inp.get("content", ""))
        if name == "list_files":
            return self._ls(inp.get("path", "."))
        if name == "ask_user":
            return self._ask_user(inp.get("question", ""))
        if name == "search_files":
            return self._search_files(inp.get("pattern", ""), inp.get("path", "."))
        if name == "git":
            return self._git(inp.get("args", ""))
        if name == "sub_task":
            return self._sub_task(inp.get("tid", ""), inp.get("task", ""), inp.get("workdir"))
        return f"unknown tool: {name}"

    def _bash(self, cmd: str) -> str:
        if _BLOCKED_BASH.search(cmd):
            return "BLOCKED: 위험한 명령어"
        self._send(f"> {cmd[:100]}")
        try:
            r = subprocess.run(  # nosec B602 -- allowlist validated by _BLOCKED_BASH before exec
                cmd, shell=True, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=60, cwd=self.workdir,
                env=self.env,
            )
            out = (r.stdout + r.stderr)[-4000:] or "(출력 없음)"
            return f"exit={r.returncode}\n{out}"
        except subprocess.TimeoutExpired:
            return "timeout (60s)"
        except Exception as e:
            return f"error: {e}"

    def _ask_user(self, question: str) -> str:
        """사용자에게 질문하고 최대 5분 대기."""
        with self._ask_lock:
            self._ask_event.clear()
            self._ask_reply = ""
            self._is_asking = True
        kb = keyboard([btn(f"T{self.tid} 답장", f"term_reply_{self.tid}")])
        self._send(f"질문: {question[:3500]}", markup=kb)
        answered = self._ask_event.wait(timeout=300)
        with self._ask_lock:
            self._is_asking = False
            reply = self._ask_reply
        if not answered or reply == "[중단됨]":
            return "[타임아웃 또는 중단] 사용자 응답 없음"
        return reply

    def _search_files(self, pattern: str, path: str) -> str:
        """grep으로 파일 내 패턴 검색."""
        base = Path(path) if Path(path).is_absolute() else Path(self.workdir) / path
        cmd = f'grep -rn --include="*.py" --include="*.js" --include="*.ts" --include="*.json" "{pattern}" "{base}" 2>&1 | head -80'
        return self._bash(cmd)

    _GIT_ALLOWED = re.compile(
        r"^(status|diff|log|add|commit|branch|show|stash|reset\s+HEAD)(\s|$)",
        re.IGNORECASE,
    )

    def _git(self, args: str) -> str:
        """허용된 git 명령만 실행."""
        args = args.strip()
        if not self._GIT_ALLOWED.match(args):
            return f"BLOCKED: 허용 git 명령 — status/diff/log/add/commit/branch/show/stash"
        cmd = f'git -C "{self.workdir}" {args}'
        return self._bash(cmd)

    def _sub_task(self, tid: str, task: str, workdir: str | None) -> str:
        """서브에이전트를 생성하고 완료까지 대기 (최대 10분)."""
        if not tid or not task:
            return "BLOCKED: tid와 task 필수"
        # 순환 호출 방지
        if tid == self.tid or tid == self.parent_tid:
            return "BLOCKED: 순환 sub_task 금지"
        sub_key = _terminal_key(self.chat_id, f"{self.tid}s{tid}")
        with _t_lock:
            if sub_key in _terminals and _terminals[sub_key].status == "running":
                return f"[T{tid}] 서브터미널 이미 실행 중"
            sub = AgentTerminal(
                tid=f"{self.tid}s{tid}",
                chat_id=self.chat_id,
                task=task,
                provider=self.provider,
                api_key=self.api_key,
                workdir=workdir or self.workdir,
                parent_tid=self.tid,
            )
            _terminals[sub_key] = sub
        sub.start()
        self._send(f"서브태스크 T{tid} 시작: {task[:60]}")
        sub._thread.join(timeout=600)
        if sub.status == "running":
            sub.stop()
            return "[서브태스크 타임아웃] 10분 초과"
        # 마지막 assistant 텍스트 수집
        last_texts = []
        for m in sub.messages[-5:]:
            if m.get("role") == "assistant":
                blocks = m.get("content", [])
                if isinstance(blocks, list):
                    for b in blocks:
                        if b.get("type") == "text" and b.get("text", "").strip():
                            last_texts.append(b["text"])
        return f"[서브태스크 완료]\n" + "\n".join(last_texts)[-3000:]

    def _read(self, path: str) -> str:
        try:
            p = Path(path) if Path(path).is_absolute() else Path(self.workdir) / path
            return p.read_text(encoding="utf-8", errors="replace")[:8000]
        except Exception as e:
            return f"error: {e}"

    def _write(self, path: str, content: str) -> str:
        try:
            p = Path(path) if Path(path).is_absolute() else Path(self.workdir) / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"written: {p} ({len(content)} chars)"
        except Exception as e:
            return f"error: {e}"

    def _ls(self, path: str) -> str:
        try:
            p = Path(path) if Path(path).is_absolute() else Path(self.workdir) / path
            items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
            return "\n".join(
                (x.name + "/" if x.is_dir() else x.name) for x in items[:60]
            )
        except Exception as e:
            return f"error: {e}"


def _terminal_key(chat_id: int, tid: str) -> str:
    return f"{chat_id}_{tid}"


def _find_awaiting_ask(chat_id: int):
    """ask_user 대기 중인 터미널 반환."""
    with _t_lock:
        for t in list(_terminals.values()):
            if t.chat_id == chat_id and t.status == "running" and t._is_asking:
                return t
    return None


def _find_running_terminal(chat_id: int):
    """실행 중인 터미널 중 tid 가장 짧은 것 반환 (서브터미널 'XsY' 제외)."""
    with _t_lock:
        running = [t for t in _terminals.values()
                   if t.chat_id == chat_id and t.status == "running"
                   and "s" not in t.tid]   # 서브터미널 키 제외
    if not running:
        return None
    return sorted(running, key=lambda t: t.tid)[0]


def _launch_terminal(chat_id: int, tid: str, task: str,
                     provider: str, api_key: str, workdir: str | None = None):
    """터미널 생성 또는 재사용."""
    key = _terminal_key(chat_id, tid)
    with _t_lock:
        old = _terminals.get(key)
        if old and old.status == "running":
            send(chat_id, f"[T{tid}] 이미 실행 중이에요. 먼저 '터미널 {tid} 중지'해주세요.")
            return
        t = AgentTerminal(tid, chat_id, task, provider, api_key, workdir)
        _terminals[key] = t
    t.start()


def _stop_terminal(chat_id: int, tid: str):
    key = _terminal_key(chat_id, tid)
    with _t_lock:
        t = _terminals.get(key)
    if not t:
        send(chat_id, f"[T{tid}] 없는 터미널이에요.")
        return
    t.stop()
    send(chat_id, f"[T{tid}] 중지했어요.")


def _terminal_status_all(chat_id: int):
    with _t_lock:
        items = [(k, v) for k, v in _terminals.items()
                 if k.startswith(f"{chat_id}_")]
    if not items:
        send(chat_id, "실행 중인 터미널이 없어요.",
             markup=keyboard([btn("메인 메뉴", "menu")]))
        return
    lines = ["[터미널 현황]"]
    for k, t in sorted(items):
        lines.append(f"  T{t.tid}: {t.status}  ({t.task[:40]})")
    send(chat_id, "\n".join(lines),
         markup=keyboard([btn("메인 메뉴", "menu")]))


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

    _log(f"[msg] chat={chat_id} text={text[:60]}")
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

PID_FILE = PROJECT_ROOT / ".claude" / "tg_commander.pid"


def _pid_alive(pid: int) -> bool:
    """Windows: tasklist로 PID가 python 프로세스인지 확인."""
    try:
        r = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5,
        )
        # 결과에 "python" 포함 여부로 판단
        return "python" in r.stdout.lower()
    except Exception:
        return False


def _acquire_lock():
    """단일 인스턴스 잠금 — 이미 실행 중이면 종료."""
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
            if _pid_alive(old_pid):
                print(f"[tg_commander] 이미 실행 중 (PID {old_pid}) — 종료합니다.")
                sys.exit(0)
            else:
                print(f"[tg_commander] stale PID {old_pid} 무시, 재시작.")
        except Exception:
            pass
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


def _release_lock():
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _force_close_other_pollers():
    """startup 시 텔레그램 close() 호출 — 다른 곳(Termux, 다른 PC)에서 polling 중이면 강제 종료시켜서 우리가 잡음.
    실패해도 무시 (이미 닫혀 있을 수 있음)."""
    try:
        r = tg_post("close", {})
        if r.get("ok"):
            _log("[tg] close() OK — 다른 polling 인스턴스 모두 종료시킴")
        else:
            _log(f"[tg] close() 응답: {r}")
        # close() 후 ~10초 대기 권장 (텔레그램이 connection cleanup)
        time.sleep(10)
    except Exception as e:
        _log(f"[tg] close() err: {e}")


def main():
    _acquire_lock()
    _log(f"[tg_commander v2] 시작 -- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} pid={os.getpid()}")

    # 다른 곳(Termux/원격)에서 같은 토큰으로 polling 중이면 강제 종료
    _force_close_other_pollers()

    broadcast(
        "BRIDGE Commander v2 시작\n"
        "========================\n"
        "버튼 메뉴로 BRIDGE 작업을 제어하세요.\n"
        "/start 또는 아무 메시지 -> 메인 메뉴",
        markup=MAIN_MENU_KB,
    )

    offset = load_offset()
    _conflict_backoff = 0
    _conflict_close_count = 0   # 409 누적 → 다시 close() 호출 트리거
    while True:
        try:
            resp = tg_get("getUpdates", {"offset": offset, "timeout": 30, "limit": 20})
            if "error_code" in resp and resp.get("error_code") == 409:
                _conflict_backoff = min(_conflict_backoff + 1, 4)
                _conflict_close_count += 1
                wait = 15 * _conflict_backoff
                _log(f"[tg] 409 Conflict — {wait}초 대기 (누적 {_conflict_close_count}회)")
                # 409가 3회 연속이면 close() 다시 호출 — 다른 poller 강제 종료
                if _conflict_close_count >= 3:
                    _log("[tg] 409 3회 — close() 재호출")
                    try: tg_post("close", {})
                    except Exception: pass
                    _conflict_close_count = 0
                    time.sleep(12)
                else:
                    time.sleep(wait)
                continue
            _conflict_close_count = 0
            _conflict_backoff = 0
            for upd in resp.get("result", []):
                uid = upd["update_id"]
                handle_update(upd)
                offset = uid + 1
                save_offset(offset)
        except KeyboardInterrupt:
            _log("[tg_commander] 종료")
            _release_lock()
            break
        except Exception as e:
            _log(f"[tg_commander] 루프 에러: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
