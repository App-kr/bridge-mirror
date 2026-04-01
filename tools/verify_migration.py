"""마이그레이션 후 복호화 검증 — 5건 샘플 확인"""
import sys, os, sqlite3
sys.path.insert(0, 'Q:/Claudework/bridge base')

try:
    from tools.bx import load_to_env
    load_to_env()
except Exception as e:
    print("BX:", e)

from security_vault import t3_decrypt, is_t3_encrypted, auto_decrypt_value

DB = 'Q:/Claudework/bridge base/master.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print("=== candidates 5건 샘플 복호화 검증 ===")
rows = conn.execute(
    "SELECT candidate_id, dob, nationality, current_location, gender "
    "FROM candidates WHERE dob IS NOT NULL LIMIT 5"
).fetchall()

ok = fail = 0
for r in rows:
    cid = r["candidate_id"]
    for col in ("dob", "nationality", "current_location", "gender"):
        val = r[col]
        if val is None:
            continue
        if is_t3_encrypted(val):
            try:
                dec = t3_decrypt(val, col)
                ok += 1
                print("  OK  cid=" + str(cid) + " " + col + " -> " + dec[:20])
            except Exception as e:
                fail += 1
                print("  FAIL cid=" + str(cid) + " " + col + " err=" + str(e))
        else:
            print("  WARN cid=" + str(cid) + " " + col + " = NOT ENCRYPTED: " + str(val)[:20])

print()
print("=== client_inquiries 5건 샘플 복호화 검증 ===")
rows2 = conn.execute(
    "SELECT id, memo, contact_name FROM client_inquiries "
    "WHERE is_deleted=0 AND memo IS NOT NULL LIMIT 5"
).fetchall()
for r in rows2:
    rid = r["id"]
    for col in ("memo", "contact_name"):
        val = r[col]
        if val is None:
            continue
        if is_t3_encrypted(val):
            try:
                dec = t3_decrypt(val, col)
                ok += 1
                print("  OK  id=" + str(rid) + " " + col + " -> " + dec[:20])
            except Exception as e:
                fail += 1
                print("  FAIL id=" + str(rid) + " " + col + " err=" + str(e))
        else:
            print("  WARN id=" + str(rid) + " " + col + " = NOT ENCRYPTED: " + str(val)[:20])

conn.close()
print()
print("=== 결과: OK=" + str(ok) + " FAIL=" + str(fail) + " ===")
sys.exit(0 if fail == 0 else 1)
