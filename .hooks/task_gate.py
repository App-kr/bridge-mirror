#!/usr/bin/env python3
"""
task_gate.py — TaskCompleted 품질 게이트
작업 완료 전 자동 검증
exit(2) → Claude Code 작업완료 차단 + 피드백

수정 이력:
  2026-03-09 — grep(Windows 미지원) → Python re 모듈로 교체
"""
import subprocess, sys, json, os, re, sqlite3

BASE = r"Q:\Claudework\bridge base"
DB   = os.path.join(BASE, "master.db")
os.chdir(BASE)

results = {}
failed  = []

# ── 1. DB integrity_check ────────────────────────
try:
    conn = sqlite3.connect(DB)
    val  = conn.execute("PRAGMA integrity_check").fetchone()[0]
    conn.close()
    results["db_integrity"] = val
    if val != "ok":
        failed.append(f"DB integrity FAIL: {val}")
except Exception as e:
    results["db_integrity"] = f"ERROR: {e}"
    failed.append("DB integrity ERROR")

# ── 2. candidates 건수 이상 감지 ─────────────────
try:
    conn  = sqlite3.connect(DB)
    count = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    conn.close()
    results["candidates_count"] = count
    if count < 3000:
        failed.append(f"candidates 이상감소: {count}건 (기준 3000+)")
except Exception as e:
    results["candidates_count"] = f"ERROR: {e}"
    failed.append("candidates count ERROR")

# ── 3. api_server.py 컴파일 ──────────────────────
try:
    r = subprocess.run(
        ["python", "-m", "py_compile", "api_server.py"],
        capture_output=True, text=True, timeout=15, cwd=BASE
    )
    results["api_compile"] = "OK" if r.returncode == 0 else r.stderr.strip()
    if r.returncode != 0:
        failed.append(f"API compile FAIL: {r.stderr.strip()[:120]}")
except Exception as e:
    results["api_compile"] = f"ERROR: {e}"
    failed.append("API compile ERROR")

# ── 4. PII 공개 라우터 노출 체크 (Python re 사용) ─
try:
    with open("api_server.py", "r", encoding="utf-8") as f:
        src = f.read()

    pub_routes = re.findall(
        r'@app\.(?:get|post)\("(?!/api/admin)(/[^"]+)"[^)]*\)\s*\n'
        r'(?:.*?\n){0,30}?(?=@app\.|$)',
        src
    )

    PII_PAT = [r'"email"\s*:', r'"phone"\s*:', r'"passport"\s*:']
    exposed  = []

    for block in pub_routes:
        for p in PII_PAT:
            if re.search(p, block) and "mask" not in block.lower():
                exposed.append(block[:60])
                break

    results["pii_public"] = "CLEAN" if not exposed else f"WARN {len(exposed)}건"
    if exposed:
        failed.append(f"PII 공개라우터 노출 의심: {len(exposed)}건 수동확인 필요")

except Exception as e:
    results["pii_public"] = f"SKIP: {e}"

# ── 5. hard-delete 감지 (Python re 사용 — grep 대체) ─
try:
    with open("api_server.py", "r", encoding="utf-8") as f:
        lines = f.readlines()

    hits = [
        f"L{i+1}: {line.strip()}"
        for i, line in enumerate(lines)
        if re.search(r"DELETE\s+FROM", line, re.IGNORECASE)
        and "is_deleted" not in line
    ]

    results["hard_delete_check"] = "CLEAN" if not hits else f"WARN: {hits[:3]}"
    if hits:
        failed.append(f"hard-delete 감지: {hits[0][:80]}")
except Exception as e:
    results["hard_delete_check"] = f"SKIP: {e}"

# ── 출력 ─────────────────────────────────────────
print("\n" + "=" * 52)
print("BRIDGE TaskCompleted Gate")
print("=" * 52)
print(json.dumps(results, ensure_ascii=False, indent=2))

if failed:
    print("\n❌ 실패 항목:")
    for item in failed:
        print(f"  - {item}")
    print("\n→ 위 항목 수정 후 재시도. 작업완료 차단.")
    sys.exit(2)

print("\n✅ 전체 게이트 통과")
