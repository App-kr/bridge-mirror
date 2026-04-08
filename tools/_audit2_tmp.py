import sqlite3
conn = sqlite3.connect(r"Q:\Claudework\bridge base\master.db")
c = conn.cursor()

# email_templates 컬럼 확인
try:
    cols = [r[1] for r in c.execute("PRAGMA table_info(email_templates)").fetchall()]
    print('email_templates컬럼:', cols)
    rows = c.execute("SELECT * FROM email_templates LIMIT 5").fetchall()
    for r in rows:
        print('  template:', r[:3])
except Exception as e:
    print('email_templates없음:', e)

# candidates 컬럼 전체
cols_all = [r[1] for r in c.execute('PRAGMA table_info(candidates)').fetchall()]
print('candidates컬럼수:', len(cols_all))
# region 관련 컬럼
region_cols = [x for x in cols_all if any(k in x.lower() for k in ['region','location','city','area'])]
print('region관련:', region_cols)

# employers 샘플
try:
    rows = c.execute("SELECT jNumber, city, name, teachingAge, status FROM employers WHERE is_deleted=0 LIMIT 3").fetchall()
    for r in rows:
        print('employer:', r)
except Exception as e:
    print('employers샘플오류:', e)

conn.close()
