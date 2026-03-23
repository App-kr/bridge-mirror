"""Canvas Sheet CRUD 테스트 — INSERT / PATCH / DELETE 검증"""
import sqlite3, uuid

DB = "Q:/Claudework/bridge base/master.db"
conn = sqlite3.connect(DB)
conn.execute("PRAGMA busy_timeout = 5000")
conn.row_factory = sqlite3.Row

NOT_DEL = "status <> 'Deleted'"

print("=" * 60)
print("BRIDGE Canvas Sheet - INSERT / PATCH / DELETE Test")
print("=" * 60)

total = conn.execute(f"SELECT COUNT(*) FROM candidates WHERE {NOT_DEL}").fetchone()[0]
max_sn = conn.execute("SELECT MAX(sheet_number) FROM candidates").fetchone()[0] or 0
print(f"[Current] Active: {total} | MAX sheet_number: {max_sn}")

# ── 1) 5건 INSERT ──
NAMES = ["TEST_Top_Alpha", "TEST_Mid_Beta", "TEST_Bot_Gamma", "TEST_Rand_Delta", "TEST_Rand_Epsilon"]
NATS = ["American", "Canadian", "British", "Australian", "South African"]
created = []
for i, (nm, nt) in enumerate(zip(NAMES, NATS)):
    cid = f"cnd_test_{uuid.uuid4().hex[:8]}"
    sn = max_sn + 1 + i
    now = "2026-03-23T00:00:00Z"
    conn.execute(
        "INSERT INTO candidates (candidate_id, full_name, nationality, status, source, source_file, sheet_number, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (cid, nm, nt, "Active", "test_auto", "test_auto", sn, now, now),
    )
    created.append({"cid": cid, "name": nm, "sn": sn})
    print(f"  [INSERT] sn={sn} {nm} ({nt})")
conn.commit()
print(f"  => {len(created)} rows inserted")

# ── 2) Verify INSERT ──
print()
print("[Test 1] Verify INSERT:")
pass_cnt = 0
for c in created:
    row = conn.execute("SELECT full_name, status, sheet_number FROM candidates WHERE candidate_id=?", (c["cid"],)).fetchone()
    ok = row and row["status"] == "Active"
    if ok:
        pass_cnt += 1
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] sn={row['sheet_number']} {row['full_name']} status={row['status']}")
print(f"  => {pass_cnt}/{len(created)} passed")

# ── 3) PATCH simulation ──
print()
print("[Test 2] PATCH (cell edit):")
patches = [
    (created[0]["cid"], "notes", "Top position edit"),
    (created[1]["cid"], "status", "Interview"),
    (created[2]["cid"], "notes", "Bottom row edit"),
    (created[3]["cid"], "stage", "interview"),
    (created[4]["cid"], "mail_tags", "interview,contract"),
]
p_cnt = 0
for cid, fld, val in patches:
    conn.execute(f"UPDATE candidates SET {fld}=?, updated_at=? WHERE candidate_id=?", (val, "2026-03-23T00:01:00Z", cid))
    v = conn.execute(f"SELECT {fld} FROM candidates WHERE candidate_id=?", (cid,)).fetchone()
    ok = v and v[0] == val
    if ok:
        p_cnt += 1
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {fld}={val}")
conn.commit()
print(f"  => {p_cnt}/{len(patches)} passed")

# ── 4) Soft DELETE ──
print()
print("[Test 3] Soft DELETE:")
d_cnt = 0
for c in created:
    conn.execute("UPDATE candidates SET status=?, updated_at=? WHERE candidate_id=?", ("Deleted", "2026-03-23T00:02:00Z", c["cid"]))
conn.commit()
for c in created:
    row = conn.execute("SELECT status FROM candidates WHERE candidate_id=?", (c["cid"],)).fetchone()
    ok = row and row["status"] == "Deleted"
    if ok:
        d_cnt += 1
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {c['name']} -> Deleted")
print(f"  => {d_cnt}/{len(created)} passed")

# ── 5) Filter check ──
after = conn.execute(f"SELECT COUNT(*) FROM candidates WHERE {NOT_DEL}").fetchone()[0]
f_ok = after == total
print()
print(f"[Test 4] Filter: before={total} after={after} [{'PASS' if f_ok else 'FAIL'}]")

# ── 6) Random mid-insert + immediate delete (3 rounds) ──
print()
print("[Test 5] Random mid-insert + delete (3 rounds):")
r_cnt = 0
for trial in range(3):
    rc = f"cnd_test_r{uuid.uuid4().hex[:6]}"
    rs = max_sn + 200 + trial
    conn.execute(
        "INSERT INTO candidates (candidate_id, full_name, nationality, status, source, source_file, sheet_number, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (rc, f"TEST_Rand_{trial}", "Irish", "Active", "test_auto", "test_auto", rs, "2026-03-23T00:03:00Z", "2026-03-23T00:03:00Z"),
    )
    conn.commit()
    e = conn.execute("SELECT COUNT(*) FROM candidates WHERE candidate_id=? AND status='Active'", (rc,)).fetchone()[0]
    conn.execute("UPDATE candidates SET status='Deleted' WHERE candidate_id=?", (rc,))
    conn.commit()
    d = conn.execute("SELECT status FROM candidates WHERE candidate_id=?", (rc,)).fetchone()
    ok = e == 1 and d["status"] == "Deleted"
    if ok:
        r_cnt += 1
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] sn={rs} insert->delete cycle")
print(f"  => {r_cnt}/3 passed")

# ── 7) Cleanup ──
conn.execute("DELETE FROM candidates WHERE source='test_auto'")
conn.commit()
rem = conn.execute("SELECT COUNT(*) FROM candidates WHERE source='test_auto'").fetchone()[0]
final = conn.execute(f"SELECT COUNT(*) FROM candidates WHERE {NOT_DEL}").fetchone()[0]
print()
print(f"[Cleanup] test_auto removed: {rem} remaining [{'PASS' if rem == 0 else 'FAIL'}]")
print(f"[Final] Active candidates: {final} (original: {total}) [{'PASS' if final == total else 'FAIL'}]")

conn.close()

# Summary
all_tests = [pass_cnt == 5, p_cnt == 5, d_cnt == 5, f_ok, r_cnt == 3, rem == 0, final == total]
tc = 5 + 5 + 5 + 1 + 3 + 1 + 1
tp = pass_cnt + p_cnt + d_cnt + (1 if f_ok else 0) + r_cnt + (1 if rem == 0 else 0) + (1 if final == total else 0)
print()
print("=" * 60)
print(f"RESULT: {tp}/{tc} tests passed {'- ALL PASS' if all(all_tests) else '- SOME FAILED'}")
print("=" * 60)
