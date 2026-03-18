"""
bridge_memory.py — Layer 2 SQLite 영구 기억 DB
사용:
  --event user_prompt  : UserPromptSubmit hook
  --event post_tool    : PostToolUse hook
  --event stop         : Stop hook (세션 요약)
  --status             : DB 상태 확인
  search <keyword>     : 키워드 검색
"""
import sys, os, json, sqlite3, argparse, io
from datetime import datetime

# Windows cp949 환경 UTF-8 출력 강제
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

DB_PATH = os.path.join(os.path.dirname(__file__), "bridge_memory.db")

# ── DB 초기화 ──────────────────────────────────
def init_db(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS messages (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        ts        TEXT    NOT NULL,
        role      TEXT    NOT NULL,
        content   TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS tool_uses (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        ts        TEXT    NOT NULL,
        tool_name TEXT    NOT NULL,
        input     TEXT,
        result    TEXT
    );
    CREATE TABLE IF NOT EXISTS sessions (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        ts        TEXT    NOT NULL,
        summary   TEXT    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_messages_ts   ON messages(ts);
    CREATE INDEX IF NOT EXISTS idx_tool_uses_ts  ON tool_uses(ts);
    CREATE INDEX IF NOT EXISTS idx_sessions_ts   ON sessions(ts);
    """)
    conn.commit()

# ── 공통 ───────────────────────────────────────
def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    return conn

# ── 이벤트 핸들러 ───────────────────────────────
def handle_user_prompt(data: dict):
    prompt = (data.get("prompt") or
              data.get("user_prompt") or
              str(data)[:500])
    conn = get_conn()
    conn.execute(
        "INSERT INTO messages(ts, role, content) VALUES(?,?,?)",
        (now(), "user", prompt[:2000])
    )
    conn.commit()
    conn.close()

def handle_post_tool(data: dict):
    tool  = data.get("tool_name", data.get("tool", "unknown"))
    inp   = json.dumps(data.get("tool_input", {}), ensure_ascii=False)[:1000]
    res   = str(data.get("tool_response", ""))[:1000]
    conn  = get_conn()
    conn.execute(
        "INSERT INTO tool_uses(ts, tool_name, input, result) VALUES(?,?,?,?)",
        (now(), tool, inp, res)
    )
    conn.commit()
    conn.close()

def handle_stop(data: dict):
    # 최근 메시지·툴 사용 요약 자동 생성
    conn = get_conn()
    recent_msgs = conn.execute(
        "SELECT role, content FROM messages ORDER BY id DESC LIMIT 10"
    ).fetchall()
    recent_tools = conn.execute(
        "SELECT tool_name, input FROM tool_uses ORDER BY id DESC LIMIT 10"
    ).fetchall()

    msg_summary  = " | ".join(f"{r}:{c[:80]}" for r, c in reversed(recent_msgs))
    tool_summary = " | ".join(f"{t}:{i[:60]}" for t, i in reversed(recent_tools))
    summary = f"[메시지] {msg_summary}\n[도구] {tool_summary}"

    conn.execute(
        "INSERT INTO sessions(ts, summary) VALUES(?,?)",
        (now(), summary[:3000])
    )
    conn.commit()
    conn.close()

# ── 상태 확인 ───────────────────────────────────
def status():
    if not os.path.exists(DB_PATH):
        print("DB 없음 — 첫 hook 실행 시 자동 생성됩니다")
        return
    conn = get_conn()
    msgs    = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    tools   = conn.execute("SELECT COUNT(*) FROM tool_uses").fetchone()[0]
    sess    = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    size_kb = os.path.getsize(DB_PATH) // 1024
    last    = conn.execute("SELECT ts FROM messages ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    print(f"DB: {DB_PATH}")
    print(f"크기: {size_kb} KB")
    print(f"메시지: {msgs}건 | 도구실행: {tools}건 | 세션: {sess}건")
    print(f"마지막 기록: {last[0] if last else '없음'}")

# ── 키워드 검색 ─────────────────────────────────
def search(keyword: str):
    if not os.path.exists(DB_PATH):
        print("DB 없음")
        return
    conn = get_conn()
    kw = f"%{keyword}%"
    print(f"=== 메시지 검색: '{keyword}' ===")
    rows = conn.execute(
        "SELECT ts, role, content FROM messages WHERE content LIKE ? ORDER BY id DESC LIMIT 10",
        (kw,)
    ).fetchall()
    for ts, role, content in rows:
        print(f"  [{ts}] {role}: {content[:120]}")

    print(f"\n=== 도구 검색: '{keyword}' ===")
    rows = conn.execute(
        "SELECT ts, tool_name, input FROM tool_uses WHERE input LIKE ? OR result LIKE ? ORDER BY id DESC LIMIT 5",
        (kw, kw)
    ).fetchall()
    for ts, tool, inp in rows:
        print(f"  [{ts}] {tool}: {inp[:100]}")

    print(f"\n=== 세션 검색: '{keyword}' ===")
    rows = conn.execute(
        "SELECT ts, summary FROM sessions WHERE summary LIKE ? ORDER BY id DESC LIMIT 3",
        (kw,)
    ).fetchall()
    for ts, summary in rows:
        print(f"  [{ts}] {summary[:150]}")
    conn.close()

# ── 진입점 ──────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event",  choices=["user_prompt", "post_tool", "stop"])
    parser.add_argument("--status", action="store_true")
    parser.add_argument("cmd",      nargs="?")   # "search"
    parser.add_argument("keyword",  nargs="?")   # 검색어
    args, _ = parser.parse_known_args()

    if args.status:
        status()
        return

    if args.cmd == "search" and args.keyword:
        search(args.keyword)
        return
    elif args.cmd == "search":
        print("사용법: bridge_memory.py search <keyword>")
        return

    if args.event:
        try:
            data = json.load(sys.stdin)
        except Exception:
            data = {}
        if args.event == "user_prompt":
            handle_user_prompt(data)
        elif args.event == "post_tool":
            handle_post_tool(data)
        elif args.event == "stop":
            handle_stop(data)
        return

    # 인자 없으면 status
    status()

if __name__ == "__main__":
    main()
