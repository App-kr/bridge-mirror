"""임시 복원 스크립트"""
from pathlib import Path
import sqlite3, io, urllib.request, urllib.error, json, re, subprocess

env_file = Path("Q:/Claudework/bridge base/.env.restored")
if not env_file.exists():
    subprocess.run(["Q:/Phtyon 3/python.exe", "-X", "utf8", "tools/bx.py", "export-env"],
                   cwd="Q:/Claudework/bridge base", capture_output=True)

env = {}
for line in env_file.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")

RENDER_API = "https://bridge-n7hk.onrender.com"
ADMIN_KEY = env.get("ADMIN_API_KEY", "")
DB_PATH = Path("Q:/Claudework/bridge base/master.db")

TARGET = ["candidates", "jobs", "client_inquiries", "interviews",
          "site_settings", "file_uploads", "mail_introduce_log"]


def quote_val(v):
    if v is None: return "NULL"
    if isinstance(v, (int, float)): return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def build_create_table(conn, table_name):
    cols = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    if not cols: return None
    col_defs = []
    pk_cols = [c[1] for c in cols if c[5] > 0]
    for col in cols:
        cid, name, typ, notnull, dflt_value, pk = col
        typ = typ or "TEXT"
        parts = [f'"{name}" {typ}']
        if len(pk_cols) == 1 and pk: parts.append("PRIMARY KEY")
        if notnull and not pk: parts.append("NOT NULL")
        if dflt_value is not None: parts.append(f"DEFAULT {dflt_value}")
        col_defs.append("    " + " ".join(parts))
    if len(pk_cols) > 1:
        col_defs.append("    PRIMARY KEY (" + ", ".join(f'"{c}"' for c in pk_cols) + ")")
    return f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n' + ",\n".join(col_defs) + "\n);"


def build_dump(conn, tables):
    buf = io.StringIO()
    buf.write("BEGIN TRANSACTION;\n")
    for t in tables:
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone()
        if not exists: continue
        create_sql = build_create_table(conn, t)
        if create_sql: buf.write(create_sql + "\n")
        for (idx_sql,) in conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL", (t,)
        ).fetchall():
            buf.write(idx_sql + ";\n")
        for row in conn.execute(f'SELECT * FROM "{t}"').fetchall():
            vals = ",".join(quote_val(v) for v in row)
            buf.write(f'INSERT OR IGNORE INTO "{t}" VALUES({vals});\n')
    buf.write("COMMIT;\n")
    return buf.getvalue()


print("[1] 덤프 생성 중...")
conn = sqlite3.connect(str(DB_PATH))
conn.execute("PRAGMA busy_timeout=5000")
sql_text = build_dump(conn, TARGET)
conn.close()
print(f"  {sql_text.count(chr(10)):,}줄, {len(sql_text.encode())//1024}KB")

print("[2] Render 복원 전송...")
boundary = "----BridgeRestoreBoundary"
sql_bytes = sql_text.encode("utf-8")
body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"sql_dump\"; filename=\"master.sql\"\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n"
        .encode() + sql_bytes + f"\r\n--{boundary}--\r\n".encode())

req = urllib.request.Request(f"{RENDER_API}/api/admin/db/restore", data=body,
    headers={"x-admin-key": ADMIN_KEY, "Content-Type": f"multipart/form-data; boundary={boundary}",
             "Content-Length": str(len(body)), "Origin": "https://bridge-chi-lime.vercel.app"}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=180) as r:
        result = json.loads(r.read())
        print(f"결과: {result.get('message')}")
        print(json.dumps(result.get('data'), ensure_ascii=False))
except urllib.error.HTTPError as e:
    print(f"[실패] HTTP {e.code}: {e.read().decode()[:300]}")
except Exception as e:
    print(f"[실패] {e}")
