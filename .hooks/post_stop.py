#!/usr/bin/env python3
"""
post_stop.py — Stop hook: 세션 종료 자동처리
실행순서:
  1. DB 백업 (영구보관 — 삭제 없음)
  2. 백업 현황 리포트
  3. git add (안전 파일만) + commit
  4. DB 스냅샷 기록
  5. 작업 로그 저장
  6. 최종 보고 출력

수정 이력:
  2026-03-09 — auto git push 제거 (사용자 명시 요청 없이 push 금지 원칙)
               git add -A → 안전 경로만 명시적 add (.bridge.key 등 민감파일 제외)
"""
import subprocess, datetime, os, json
import shutil, glob, sqlite3

BASE       = r"Q:\Claudework\bridge base"
BACKUP_DIR = os.path.join(BASE, ".backups")
LOG_DIR    = os.path.join(BASE, ".logs")
DB_PATH    = os.path.join(BASE, "master.db")

os.chdir(BASE)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(LOG_DIR,    exist_ok=True)

ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log = {"timestamp": ts, "steps": {}}

# ── 1. DB 백업 (영구보관) ────────────────────────
try:
    dst = os.path.join(BACKUP_DIR, f"master_{ts}.db")
    shutil.copy2(DB_PATH, dst)
    size_kb = os.path.getsize(dst) // 1024
    log["steps"]["db_backup"] = f"✅ master_{ts}.db ({size_kb}KB)"
except Exception as e:
    log["steps"]["db_backup"] = f"❌ {e}"

# ── 2. 백업 현황 리포트 (삭제 없음) ─────────────
try:
    all_bk   = sorted(glob.glob(os.path.join(BACKUP_DIR, "master_*.db")))
    total_mb = sum(os.path.getsize(f) for f in all_bk) // (1024 * 1024)
    log["steps"]["backup_status"] = (
        f"✅ 전체 {len(all_bk)}개 영구보관 / 누적 {total_mb}MB"
    )
except Exception as e:
    log["steps"]["backup_status"] = f"❌ {e}"

# ── 3. git add (안전 경로만) + commit ─────────────
# .bridge.key, .env 등 민감파일 제외 — git add -A 사용 금지
SAFE_ADD_PATHS = [
    "api_server.py",
    "web_frontend/",
    ".hooks/",
    ".claude/settings.json",
    "tasks/",
    "CLAUDE.md",
]

try:
    for path in SAFE_ADD_PATHS:
        if os.path.exists(os.path.join(BASE, path)):
            subprocess.run(["git", "add", path], cwd=BASE, timeout=15)
    r = subprocess.run(
        ["git", "commit", "-m", f"AUTO-STOP: {ts} 세션종료 자동백업"],
        capture_output=True, text=True, cwd=BASE, timeout=30
    )
    out = (r.stdout + r.stderr).strip()
    log["steps"]["git_commit"] = f"✅ {out[:100]}"
except Exception as e:
    log["steps"]["git_commit"] = f"❌ {e}"

# ── 4. DB 스냅샷 ─────────────────────────────────
try:
    conn = sqlite3.connect(DB_PATH)
    snap = {
        "candidates":       conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0],
        "client_inquiries": conn.execute("SELECT COUNT(*) FROM client_inquiries").fetchone()[0],
        "jobs":             conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
    }
    conn.close()
    log["steps"]["db_snapshot"] = snap
except Exception as e:
    log["steps"]["db_snapshot"] = f"❌ {e}"

# ── 5. 다음 작업 추천 ────────────────────────────
log["next_steps"] = [
    "Gmail 수신연동 — 채용의뢰 접수 시 is_new=1 자동 세팅",
    "구인자관리 PII 마스킹 제거 최종 검증 (admin 전체 노출)",
    "Jobs 모달 전체 필드 표시 검증 — 12개 항목 전부 확인",
]

# ── 6. 로그 저장 ─────────────────────────────────
log_path = os.path.join(LOG_DIR, f"work_{ts}.json")
with open(log_path, "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)

# ── 최종 출력 ────────────────────────────────────
print("\n" + "=" * 52)
print("✅ BRIDGE 세션 종료 자동처리 완료")
print("=" * 52)
for k, v in log["steps"].items():
    label = str(v)
    print(f"  {k:20s} {label}")
print(f"\n📁 로그:  {log_path}")
print(f"🔒 백업:  .backups/master_{ts}.db")
print("\n📋 내일 추천 작업:")
for i, s in enumerate(log["next_steps"], 1):
    print(f"  {i}. {s}")
