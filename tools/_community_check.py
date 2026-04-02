import sqlite3

conn = sqlite3.connect(r"Q:\Claudework\bridge base\master.db")
c = conn.cursor()

# community_posts 현황
c.execute("SELECT COUNT(*) FROM community_posts WHERE is_deleted=0")
total = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM community_posts WHERE is_deleted=0 AND board='korea'")
korea = c.fetchone()[0]
c.execute("SELECT id, board, title, sort_order, created_at FROM community_posts WHERE is_deleted=0 ORDER BY board, sort_order DESC, created_at DESC LIMIT 20")
rows = c.fetchall()

# file_uploads community 이미지
c.execute("SELECT COUNT(*) FROM file_uploads WHERE entity_type='community' AND is_deleted=0")
imgs = c.fetchone()[0]
c.execute("SELECT id, entity_id, file_url, created_at FROM file_uploads WHERE entity_type='community' AND is_deleted=0 LIMIT 10")
img_rows = c.fetchall()

print("=== community_posts ===")
print(f"Total active: {total}, Korea board: {korea}")
print("Top 20 by board/sort_order:")
for r in rows:
    print(f"  id={r[0]} board={r[1]} title={str(r[2])[:50]} sort={r[3]} created={r[4]}")

print(f"\n=== file_uploads (community) ===")
print(f"Image records: {imgs}")
for r in img_rows:
    print(f"  id={r[0]} entity_id={r[1]} url={str(r[2])[:80]} created={r[3]}")

conn.close()
