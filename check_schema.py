import sqlite3
conn = sqlite3.connect("Q:/Claudework/bridge base/master.db")

print("=== jobs ===")
rows = conn.execute("PRAGMA table_info(jobs)").fetchall()
for r in rows:
    print(r)

print()
print("=== client_inquiries ===")
rows2 = conn.execute("PRAGMA table_info(client_inquiries)").fetchall()
for r in rows2:
    print(r)

print()
print("jobs rows:", conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])
print("client_inquiries rows:", conn.execute("SELECT COUNT(*) FROM client_inquiries").fetchone()[0])

print()
print("=== jobs sample (1 row) ===")
r = conn.execute("SELECT * FROM jobs LIMIT 1").fetchone()
if r:
    cols = [d[0] for d in conn.execute("PRAGMA table_info(jobs)").fetchall()]
    for c, v in zip(cols, r):
        print(f"  {c}: {str(v)[:80]}")

print()
print("=== client_inquiries sample (1 row) ===")
r2 = conn.execute("SELECT * FROM client_inquiries LIMIT 1").fetchone()
if r2:
    cols2 = [d[0] for d in conn.execute("PRAGMA table_info(client_inquiries)").fetchall()]
    for c, v in zip(cols2, r2):
        print(f"  {c}: {str(v)[:80]}")

conn.close()
