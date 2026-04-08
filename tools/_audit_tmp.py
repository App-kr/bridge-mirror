import sqlite3
conn = sqlite3.connect(r"Q:\Claudework\bridge base\master.db")
c = conn.cursor()

tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
emp_t = [t for t in tables if any(x in t.lower() for x in ['employ','client','company'])]
print('employer관련:', emp_t)

try:
    cols = [r[1] for r in c.execute('PRAGMA table_info(employers)').fetchall()]
    print('employers컬럼:', cols)
    cnt = c.execute('SELECT COUNT(*) FROM employers').fetchone()[0]
    print('employers행수:', cnt)
except Exception as e:
    print('employers없음:', e)

try:
    rows = c.execute("SELECT id, name, subject FROM email_templates").fetchall()
    print('templates:', rows)
except Exception as e:
    print('email_templates없음:', e)

try:
    rows = c.execute("SELECT sheet_number, nationality, gender, region, cert, experience, start_date, target_age, housing, preference FROM candidates WHERE status='active' AND sheet_number IS NOT NULL ORDER BY id DESC LIMIT 3").fetchall()
    for r in rows:
        print('candidate:', r)
except Exception as e:
    print('candidates오류:', e)

cols_all = [r[1] for r in c.execute('PRAGMA table_info(candidates)').fetchall()]
talent_cols = [x for x in cols_all if any(k in x.lower() for k in ['talent','dislike','summary','salary','badge','reference'])]
print('talent관련컬럼:', talent_cols)

try:
    c.execute('SELECT COUNT(*) FROM mail_send_queue')
    print('mail_send_queue: 있음')
except:
    print('mail_send_queue: 없음')

try:
    c.execute('SELECT COUNT(*) FROM mail_introduce_log')
    print('mail_introduce_log: 있음')
except:
    print('mail_introduce_log: 없음')

conn.close()
