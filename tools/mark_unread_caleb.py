"""Caleb Shannon 메일 읽지않음 복원 + email_logs에서 오발송 기록 제거
긴급 수정용 1회성 스크립트
"""
import imaplib
import sqlite3
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── 크리덴셜 로딩 ─────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

GMAIL_ADDR = os.environ.get("GMAIL_ADDRESS") or os.environ.get("GMAIL_USER", "bridgejobkr@gmail.com")
GMAIL_PASS = os.environ.get("GMAIL_APP_PASSWORD", "")

CALEB_EMAIL = "caleb.shannon7890@gmail.com"

def main():
    if not GMAIL_PASS:
        print("❌ GMAIL_APP_PASSWORD 미설정 → .env 확인")
        return

    # ── 1) IMAP: Caleb 관련 메일 읽지않음 복원 ──────────────────────────────
    print(f"[IMAP] {GMAIL_ADDR} 연결 중...")
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(GMAIL_ADDR, GMAIL_PASS)
    imap.select("INBOX")

    # Caleb 발신 메일 전체 검색 (읽음 + 안읽음 모두)
    _, data = imap.search(None, f'FROM "{CALEB_EMAIL}"')
    uid_list = data[0].split() if data[0] else []
    print(f"[IMAP] Caleb 메일 {len(uid_list)}건 발견")

    restored = 0
    for uid_b in uid_list:
        # 현재 플래그 확인
        _, flag_data = imap.fetch(uid_b, "(FLAGS)")
        flags_str = flag_data[0].decode() if flag_data and flag_data[0] else ""
        if "\\Seen" in flags_str:
            imap.store(uid_b, "-FLAGS", "\\Seen")
            restored += 1
            print(f"  → uid={uid_b.decode()} 읽지않음 복원")
        else:
            print(f"  → uid={uid_b.decode()} 이미 안읽음")

    imap.logout()
    print(f"[IMAP] 완료: {restored}건 읽지않음 복원")

    # ── 2) DB: email_logs 오발송 기록 제거 ──────────────────────────────────
    DB_PATH = PROJECT_ROOT / "master.db"
    if DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH))
        try:
            rows = conn.execute(
                "SELECT id, subject, sent_at FROM email_logs WHERE from_email=? AND status='SENT'",
                (CALEB_EMAIL,)
            ).fetchall()
            if rows:
                print(f"\n[DB] email_logs SENT 기록 {len(rows)}건 발견:")
                for r in rows:
                    print(f"  id={r[0]} | {r[2]} | {r[1]}")
                conn.execute(
                    "DELETE FROM email_logs WHERE from_email=? AND status='SENT'",
                    (CALEB_EMAIL,)
                )
                conn.commit()
                print(f"[DB] {len(rows)}건 삭제 완료 → 다음 폴링에서 재처리 안함")
            else:
                print("\n[DB] email_logs SENT 기록 없음 (정상)")
        finally:
            conn.close()

    # ── 3) email_processed.json에서 Caleb 관련 Message-ID 제거 ─────────────
    PROCESSED_FILE = PROJECT_ROOT / ".claude" / "email_processed.json"
    if PROCESSED_FILE.exists():
        import json
        with open(PROCESSED_FILE, encoding="utf-8") as f:
            processed = json.load(f)
        if isinstance(processed, list):
            before = len(processed)
            processed_new = [x for x in processed if CALEB_EMAIL not in str(x)]
            if len(processed_new) < before:
                with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
                    json.dump(processed_new, f)
                print(f"[JSON] processed.json {before-len(processed_new)}건 제거")
            else:
                print("[JSON] processed.json 관련 항목 없음")

    print("\n✅ 완료. Caleb 메일 읽지않음 복원 + 오발송 기록 정리")

if __name__ == "__main__":
    main()
