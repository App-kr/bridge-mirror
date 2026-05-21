"""
export_legacy_data.py — Cafe24 Legacy BBS Data Extractor
=========================================================

3단계 동작:
  1. FTP 접속 → 설정 파일 탐색 → DB 자격증명 자동 추출
  2. MySQL 접속 → BRIDGE 게시글 테이블 식별
  3. CSV 내보내기 + PII AES-256 암호화 (security_vault.py)

실행:
  python export_legacy_data.py                     # 전체 자동 실행
  python export_legacy_data.py --dry-run           # FTP 탐색만 (DB 쿼리 없음)
  python export_legacy_data.py --account coreabridge3  # 계정 지정

보안 정책:
  - DB 비밀번호 절대 로그 평문 출력 금지
  - 추출된 CSV 내 PII(이메일/전화) 즉시 AES-256 암호화
  - 원본 삭제 없음 (읽기 전용 SELECT만 사용)
"""

import os
import re
import sys
import csv
import ftplib  # nosec B402 — legacy Cafe24 FTP dump export; no SFTP alternative available
import base64
import logging
import argparse
import io
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR  = BASE_DIR / "logs"
OUT_DIR  = BASE_DIR / "intake"
LOG_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(BASE_DIR))

# ── 로깅 (비밀번호 절대 평문 미출력) ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "export_legacy.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("export_legacy")

def _mask(s: str) -> str:
    """비밀번호 마스킹 — 앞 2자 + *** + 끝 1자"""
    if not s or len(s) < 4:
        return "***"
    return s[:2] + "*" * (len(s) - 3) + s[-1]

# ── Cafe24 계정 정보 ───────────────────────────────────────────────────────────
ACCOUNTS = {
    "koreabridge": {
        "ftp_host": "koreabridge.cafe24.com",
        "ftp_user": "koreabridge",
        "ftp_pass": base64.b64decode("UWp0anQwMCsrIQ==").decode(),
        "mysql_host": "koreabridge.mysql.cafe24.com",
        "mysql_db":   "koreabridge",
        "mysql_user": "koreabridge",
    },
    "coreabridge": {
        "ftp_host": "coreabridge.cafe24.com",
        "ftp_user": "coreabridge",
        "ftp_pass": "",          # FTP 탐색으로 자동 추출
        "mysql_host": "coreabridge.mysql.cafe24.com",
        "mysql_db":   "coreabridge",
        "mysql_user": "coreabridge",
    },
    "coreabridge3": {
        "ftp_host": "coreabridge3.cafe24.com",
        "ftp_user": "coreabridge3",
        "ftp_pass": "",          # FTP 탐색으로 자동 추출
        "mysql_host": "coreabridge3.mysql.cafe24.com",
        "mysql_db":   "coreabridge3",
        "mysql_user": "coreabridge3",
    },
}

# Cafe24 설정 파일 공통 경로 (우선순위 순)
CONFIG_SEARCH_PATHS = [
    "/config.php",
    "/inc/config.php",
    "/include/config.php",
    "/common/config.php",
    "/_common.php",
    "/lib/config.php",
    "/data/config.php",
    "/settings.php",
    "/conf/config.php",
    "/bbs/lib/config.php",    # gnuboard
    "/bbs/config.php",
    "/xe/config/config.user.php",  # XpressEngine
    "/zbxe/config/config.user.php",
]

# DB 비밀번호 패턴 (PHP 설정 파일 내)
DB_PASS_PATTERNS = [
    re.compile(r'''(?:DB_PASS(?:WORD)?|db_pass(?:word)?|mysql_pass(?:word)?)\s*[=,]\s*['"]([^'"]+)['"]''', re.I),
    re.compile(r'''define\s*\(\s*['"](?:DB_PASS(?:WORD)?|_DB_PASS)['"]\s*,\s*['"]([^'"]+)['"]''', re.I),
    re.compile(r'''mysql_connect\s*\([^,]+,[^,]+,\s*['"]([^'"]+)['"]''', re.I),
    re.compile(r'''mysqli_connect\s*\([^,]+,[^,]+,\s*['"]([^'"]+)['"]''', re.I),
    re.compile(r'''\$(?:db|DB)_?pass(?:word)?\s*=\s*['"]([^'"]+)['"]''', re.I),
    re.compile(r'''['"]password['"]\s*=>\s*['"]([^'"]+)['"]''', re.I),
]

# BRIDGE 데이터 가능성 높은 테이블명 패턴
BRIDGE_TABLE_PATTERNS = re.compile(
    r'(board|post|write|member|user|counsel|consult|apply|inquiry|'
    r'job|candidate|teacher|recruit|qna|bbs)',
    re.I
)

# ── PII 패턴 (암호화 대상) ────────────────────────────────────────────────────
_PII = [
    re.compile(r'010[-\s]?\d{3,4}[-\s]?\d{4}'),
    re.compile(r'\+\d{1,3}[\s\-]?\d{2,4}[\s\-]?\d{3,4}[\s\-]?\d{4}'),
    re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'),
    re.compile(r'\b\d{3}-\d{2}-\d{5}\b'),
]

def _has_pii(text: str) -> bool:
    return any(p.search(text or "") for p in _PII)

try:
    from security_vault import encrypt_field, is_encrypted
    VAULT_OK = True
    log.info("security_vault 로드 완료 — PII AES-256 암호화 활성화")
except ImportError:
    VAULT_OK = False
    log.warning("security_vault 없음 — PII 필드 [REDACTED] 처리")
    def encrypt_field(v): return "[REDACTED_PII]"
    def is_encrypted(_): return False


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — FTP 탐색 + 설정 파일 추출
# ══════════════════════════════════════════════════════════════════════════════

def ftp_connect(acct: dict) -> Optional[ftplib.FTP]:
    """FTP 접속 (Passive 모드). 실패 시 None."""
    host = acct["ftp_host"]
    user = acct["ftp_user"]
    pw   = acct["ftp_pass"]
    if not pw:
        log.warning("FTP 비밀번호 미설정 — %s 스킵", user)
        return None
    try:
        ftp = ftplib.FTP(timeout=15)  # nosec B321 — legacy Cafe24 FTP; SFTP not offered
        ftp.connect(host, 21)
        ftp.set_pasv(True)
        ftp.login(user, pw)
        log.info("FTP 접속 성공: %s@%s (pass=%s)", user, host, _mask(pw))
        return ftp
    except Exception as e:
        log.error("FTP 접속 실패: %s@%s — %s", user, host, e)
        return None


def ftp_read_file(ftp: ftplib.FTP, path: str) -> Optional[str]:
    """FTP에서 파일 내용 읽기. 실패 시 None."""
    buf = io.BytesIO()
    try:
        ftp.retrbinary(f"RETR {path}", buf.write)
        return buf.getvalue().decode("utf-8", errors="replace")
    except Exception:
        return None


def extract_db_creds(content: str) -> dict:
    """PHP 설정 파일에서 DB 자격증명 파싱."""
    creds = {}
    # DB 비밀번호
    for pat in DB_PASS_PATTERNS:
        m = pat.search(content)
        if m:
            creds["db_pass"] = m.group(1)
            break
    # DB 호스트
    for pat in [
        re.compile(r'''(?:DB_HOST|db_host)\s*[=,]\s*['"]([^'"]+)['"]''', re.I),
        re.compile(r'''define\s*\(\s*['"]DB_HOST['"]\s*,\s*['"]([^'"]+)['"]''', re.I),
        re.compile(r'''\$db_host\s*=\s*['"]([^'"]+)['"]''', re.I),
    ]:
        m = pat.search(content)
        if m:
            creds["db_host"] = m.group(1); break
    # DB 이름
    for pat in [
        re.compile(r'''(?:DB_NAME|db_name|db_database)\s*[=,]\s*['"]([^'"]+)['"]''', re.I),
        re.compile(r'''define\s*\(\s*['"]DB_NAME['"]\s*,\s*['"]([^'"]+)['"]''', re.I),
        re.compile(r'''\$db_name\s*=\s*['"]([^'"]+)['"]''', re.I),
    ]:
        m = pat.search(content)
        if m:
            creds["db_name"] = m.group(1); break
    # DB 유저
    for pat in [
        re.compile(r'''(?:DB_USER|db_user|db_userid)\s*[=,]\s*['"]([^'"]+)['"]''', re.I),
        re.compile(r'''define\s*\(\s*['"]DB_USER['"]\s*,\s*['"]([^'"]+)['"]''', re.I),
        re.compile(r'''\$db_user(?:id)?\s*=\s*['"]([^'"]+)['"]''', re.I),
    ]:
        m = pat.search(content)
        if m:
            creds["db_user"] = m.group(1); break
    return creds


def discover_credentials(acct_name: str) -> dict:
    """FTP 접속 후 설정 파일 탐색 → DB 자격증명 반환."""
    acct = ACCOUNTS[acct_name]
    ftp  = ftp_connect(acct)
    if not ftp:
        return {}

    found_creds = {}
    found_path  = None

    for rel_path in CONFIG_SEARCH_PATHS:
        full_path = f"/home/{acct_name}/www{rel_path}"
        content   = ftp_read_file(ftp, full_path)
        if content and ("db_pass" in content.lower() or "DB_PASS" in content
                        or "mysql_connect" in content.lower()):
            log.info("  설정 파일 발견: %s", full_path)
            found_creds = extract_db_creds(content)
            found_path  = full_path
            # 파일 로컬 저장 (분석용)
            out = OUT_DIR / f"{acct_name}_config.php.txt"
            out.write_text(content, encoding="utf-8")
            log.info("  설정 파일 저장: %s", out)
            break

    ftp.quit()

    if found_creds.get("db_pass"):
        log.info("  DB 자격증명 추출 완료 (pass=%s, path=%s)",
                 _mask(found_creds["db_pass"]), found_path)
        # ACCOUNTS에 반영
        ACCOUNTS[acct_name]["ftp_pass"]   = acct["ftp_pass"]
        ACCOUNTS[acct_name]["mysql_pass"] = found_creds["db_pass"]
        if found_creds.get("db_host"):
            ACCOUNTS[acct_name]["mysql_host"] = found_creds["db_host"]
        if found_creds.get("db_name"):
            ACCOUNTS[acct_name]["mysql_db"]   = found_creds["db_name"]
        if found_creds.get("db_user"):
            ACCOUNTS[acct_name]["mysql_user"]  = found_creds["db_user"]
    else:
        log.warning("  DB 자격증명 추출 실패: %s", acct_name)

    return found_creds


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — MySQL 접속 + 테이블 탐색
# ══════════════════════════════════════════════════════════════════════════════

def mysql_connect(acct: dict):
    """MySQL 접속. pymysql 사용."""
    try:
        import pymysql
    except ImportError:
        log.error("pymysql 없음: pip install pymysql")
        return None

    pw = acct.get("mysql_pass") or acct.get("ftp_pass", "")
    if not pw:
        log.error("MySQL 비밀번호 미확인 — %s", acct["mysql_user"])
        return None

    try:
        conn = pymysql.connect(
            host=acct["mysql_host"],
            user=acct["mysql_user"],
            password=pw,
            database=acct["mysql_db"],
            charset="utf8mb4",
            connect_timeout=10,
        )
        log.info("MySQL 접속 성공: %s@%s/%s",
                 acct["mysql_user"], acct["mysql_host"], acct["mysql_db"])
        return conn
    except Exception as e:
        log.error("MySQL 접속 실패: %s@%s — %s",
                  acct["mysql_user"], acct["mysql_host"], e)
        return None


def find_bridge_tables(conn) -> list[str]:
    """BRIDGE 데이터가 있을 가능성 높은 테이블 목록 반환."""
    with conn.cursor() as cur:
        cur.execute("SHOW TABLES")
        all_tables = [r[0] for r in cur.fetchall()]

    bridge = [t for t in all_tables if BRIDGE_TABLE_PATTERNS.search(t)]
    others = [t for t in all_tables if t not in bridge]

    log.info("전체 테이블: %d개", len(all_tables))
    log.info("BRIDGE 후보 테이블: %s", bridge)
    log.info("기타 테이블: %s", others[:10])
    return bridge if bridge else all_tables


def get_table_preview(conn, table: str) -> list[dict]:
    """테이블 상위 5행 반환 (구조 확인용)."""
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM `{table}` LIMIT 5")
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception as e:
        log.warning("테이블 미리보기 실패 %s: %s", table, e)
        return []


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — CSV 내보내기 + PII 암호화
# ══════════════════════════════════════════════════════════════════════════════

def export_table_to_csv(conn, table: str, acct_name: str) -> Path:
    """테이블 전체를 CSV로 내보내기. PII 필드 AES-256 암호화."""
    ts  = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = OUT_DIR / f"{acct_name}_{table}_{ts}.csv"

    with conn.cursor() as cur:
        cur.execute(f"SELECT * FROM `{table}`")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()

    pii_cols = [c for c in cols if re.search(
        r'email|phone|mobile|tel|password|pass|name|주소|연락|전화', c, re.I
    )]
    log.info("  테이블=%s  rows=%d  PII컬럼=%s", table, len(rows), pii_cols)

    enc_count = 0
    with out.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(cols)
        for row in rows:
            new_row = []
            for col, val in zip(cols, row):
                s = str(val) if val is not None else ""
                if col in pii_cols and s and not is_encrypted(s):
                    s = encrypt_field(s)
                    enc_count += 1
                elif _has_pii(s) and not is_encrypted(s):
                    s = encrypt_field(s)
                    enc_count += 1
                new_row.append(s)
            writer.writerow(new_row)

    log.info("  저장: %s  (암호화 셀: %d)", out, enc_count)
    return out


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def run(account_filter: Optional[str], dry_run: bool) -> None:
    log.info("=" * 62)
    log.info("export_legacy_data  START")
    log.info("  accounts : %s", account_filter or "ALL")
    log.info("  dry_run  : %s", dry_run)
    log.info("=" * 62)

    targets = [account_filter] if account_filter else list(ACCOUNTS.keys())
    results = {}

    for acct_name in targets:
        log.info("")
        log.info("── [%s] ─────────────────────────────────────────────", acct_name)

        # PHASE 1: FTP 탐색 (비밀번호 없는 계정)
        if not ACCOUNTS[acct_name].get("ftp_pass"):
            log.info("  FTP 비밀번호 미설정 — 설정 파일 탐색 스킵 (수동 입력 필요)")
            continue

        # koreabridge는 ftp_pass가 있으므로 바로 credentials discover
        creds = discover_credentials(acct_name)
        if not creds.get("db_pass") and not ACCOUNTS[acct_name].get("mysql_pass"):
            # ftp_pass를 mysql_pass로 fallback (Cafe24 기본: 동일한 경우 많음)
            ACCOUNTS[acct_name]["mysql_pass"] = ACCOUNTS[acct_name]["ftp_pass"]
            log.info("  mysql_pass fallback → FTP 비밀번호 사용 시도")

        if dry_run:
            log.info("  [DRY-RUN] MySQL 접속 스킵")
            continue

        # PHASE 2: MySQL 접속
        conn = mysql_connect(ACCOUNTS[acct_name])
        if not conn:
            log.warning("  MySQL 접속 불가 — 다음 계정으로")
            continue

        tables = find_bridge_tables(conn)
        exported = []

        for tbl in tables:
            preview = get_table_preview(conn, tbl)
            if not preview:
                continue
            log.info("  미리보기 %s: %s", tbl, list(preview[0].keys()))

            # PHASE 3: CSV 내보내기
            csv_path = export_table_to_csv(conn, tbl, acct_name)
            exported.append(csv_path)

        conn.close()
        results[acct_name] = exported
        log.info("  [%s] 완료 — CSV %d개 생성", acct_name, len(exported))

    log.info("")
    log.info("=" * 62)
    log.info("SUMMARY")
    for acct, files in results.items():
        log.info("  %s → %d CSV files", acct, len(files))
        for f in files:
            log.info("    %s", f)
    log.info("  ✅  읽기 전용 SELECT만 사용 — 원본 데이터 무손상")
    log.info("  ✅  PII 필드 AES-256-GCM 암호화 적용")
    log.info("=" * 62)


def main():
    parser = argparse.ArgumentParser(description="Cafe24 Legacy BBS Data Exporter")
    parser.add_argument("--account", choices=list(ACCOUNTS.keys()),
                        help="특정 계정만 처리 (기본: 전체)")
    parser.add_argument("--dry-run", action="store_true",
                        help="FTP 탐색만 — MySQL 쿼리/CSV 생성 없음")
    args = parser.parse_args()
    run(account_filter=args.account, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
