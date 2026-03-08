"""
채용의뢰 데이터 오염 정리
- vacancies 컬럼에 들어간 근무시간 데이터 → working_hours로 이동
- housing_type 컬럼에 들어간 식사 데이터 → meal로 이동
"""
import sqlite3, re

DB = "master.db"
conn = sqlite3.connect(DB)
conn.execute("PRAGMA busy_timeout = 5000")
cur = conn.cursor()

# ── 1. vacancies 오염 정리 ──────────────────────────────────
time_pattern = re.compile(r'\d{1,2}[:~]\d{2}|\d{1,2}\s*[-~]\s*\d{1,2}')

cur.execute("SELECT id, vacancies, working_hours FROM client_inquiries WHERE vacancies IS NOT NULL AND vacancies != ''")
rows = cur.fetchall()

move_to_hours = []
clear_only_vac = []

for id_, vac, wh in rows:
    if vac and time_pattern.search(vac):
        if not wh or wh.strip() == '':
            move_to_hours.append((id_, vac))
        else:
            clear_only_vac.append(id_)

print(f"[vacancies] working_hours로 이동: {len(move_to_hours)}건")
print(f"[vacancies] NULL만 처리: {len(clear_only_vac)}건")

# 이동
for id_, vac in move_to_hours:
    cur.execute("UPDATE client_inquiries SET working_hours = ?, vacancies = NULL WHERE id = ?", (vac, id_))

# NULL만
if clear_only_vac:
    cur.executemany("UPDATE client_inquiries SET vacancies = NULL WHERE id = ?", [(i,) for i in clear_only_vac])

# ── 2. housing_type 오염 정리 ──────────────────────────────
meal_pattern = re.compile(r'meal|food|lunch|dinner|breakfast', re.IGNORECASE)

cur.execute("SELECT id, housing_type, meal FROM client_inquiries WHERE housing_type IS NOT NULL AND housing_type != ''")
rows2 = cur.fetchall()

move_to_meal = []
clear_only_ht = []

for id_, ht, meal in rows2:
    if ht and meal_pattern.search(ht):
        if not meal or meal.strip() == '':
            move_to_meal.append((id_, ht))
        else:
            clear_only_ht.append(id_)

print(f"[housing_type] meal로 이동: {len(move_to_meal)}건")
print(f"[housing_type] NULL만 처리: {len(clear_only_ht)}건")

for id_, ht in move_to_meal:
    cur.execute("UPDATE client_inquiries SET meal = ?, housing_type = NULL WHERE id = ?", (ht, id_))

if clear_only_ht:
    cur.executemany("UPDATE client_inquiries SET housing_type = NULL WHERE id = ?", [(i,) for i in clear_only_ht])

conn.commit()

# ── 검증 ───────────────────────────────────────────────────
cur.execute("PRAGMA integrity_check")
print("integrity:", cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM client_inquiries")
print("total:", cur.fetchone()[0])

conn.close()
print("완료")
