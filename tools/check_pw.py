import sqlite3
conn = sqlite3.connect(r"Q:\Claudework\bridge base\master.db")
cur = conn.cursor()
cur.execute("SELECT key, LENGTH(enc_value), SUBSTR(enc_value,1,15) FROM app_secrets")
for row in cur.fetchall():
    print(f"  key={row[0]!r} val_len={row[1]} prefix={row[2]!r}")
conn.close()
