import sqlite3

conn = sqlite3.connect(r"Q:\Claudework\bridge base\master.db")
c = conn.cursor()
c.execute("SELECT id, board, title, created_at FROM community_posts WHERE board = 'visa' ORDER BY id")
rows = c.fetchall()
for r in rows:
    print(str(r).encode('utf-8', errors='replace').decode('utf-8'))
conn.close()
