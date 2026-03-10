import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('master.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, board, title FROM community_posts WHERE is_deleted=0 ORDER BY board, id")
for r in cur.fetchall():
    print(f"[{r['board']}] #{r['id']} {r['title'][:70]}")
conn.close()
