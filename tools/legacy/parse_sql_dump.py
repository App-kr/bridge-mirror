"""
parse_sql_dump.py — Cafe24 MySQL 덤프(.sql) → legacy_posts.csv 변환기
======================================================================

Cafe24 "DATA&DB복원/백업" 메뉴에서 다운로드한 .sql 파일을
migrate_bbs.py 입력 형식(legacy_posts.csv)으로 변환합니다.

지원 덤프 형식:
  - mysqldump 표준 형식 (INSERT INTO ... VALUES ...)
  - phpMyAdmin 내보내기 형식
  - Cafe24 자동 백업 형식

사용법:
  python parse_sql_dump.py --sql dump.sql
  python parse_sql_dump.py --sql dump.sql --table xe_documents   # 테이블 지정
  python parse_sql_dump.py --sql dump.sql --list-tables          # 테이블 목록 출력
  python parse_sql_dump.py --sql dump.sql --dry-run              # 파싱만 (CSV 저장 안함)
  python parse_sql_dump.py --sql dump.sql --board visa           # board 강제 지정
  python parse_sql_dump.py --sql dump.sql --encoding euc-kr      # 인코딩 지정

출력:
  legacy_posts.csv (migrate_bbs.py 입력으로 바로 사용 가능)

지원 BBS 테이블 패턴 (자동 감지):
  - xe_documents, xe_board_*, bbs_*, board_*, post_*, article_*
  - gnuboard5_*, g5_write_*, write_*, zb_*
"""

import re
import sys
import csv
import logging
import argparse
from pathlib import Path
from typing import Iterator

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("parse_sql_dump")

# ── BBS 테이블 패턴 (자동 감지용) ────────────────────────────────────────────
BBS_TABLE_PATTERNS = [
    # XE (XpressEngine) — 많은 한국 사이트
    re.compile(r"^xe_documents$", re.I),
    re.compile(r"^xe_board_", re.I),
    # 그누보드5 (Gnuboard5)
    re.compile(r"^g5_write_", re.I),
    re.compile(r"^gnuboard5_write_", re.I),
    # 제로보드
    re.compile(r"^zb_", re.I),
    # 일반적인 BBS 테이블명
    re.compile(r"^bbs_", re.I),
    re.compile(r"^board_", re.I),
    re.compile(r"^post", re.I),
    re.compile(r"^article", re.I),
    re.compile(r"^write_", re.I),
    re.compile(r"_board$", re.I),
    re.compile(r"_post$", re.I),
    re.compile(r"_bbs$", re.I),
]

# ── 컬럼 매핑 (다양한 BBS 스키마 → 표준 필드) ────────────────────────────────
# (정규화된 컬럼명 → 표준 필드명)
COLUMN_MAP = {
    # 제목
    "title": "title",
    "subject": "title",
    "제목": "title",
    # 본문
    "content": "content",
    "body": "content",
    "contents": "content",
    "본문": "content",
    "내용": "content",
    # 작성자
    "author": "author",
    "writer": "author",
    "nick_name": "author",
    "nickname": "author",
    "mb_id": "author",
    "작성자": "author",
    "닉네임": "author",
    # 날짜
    "created_at": "created_at",
    "regdate": "created_at",
    "reg_date": "created_at",
    "write_date": "created_at",
    "date": "created_at",
    "wdate": "created_at",
    "input_date": "created_at",
    "register_date": "created_at",
    # 삭제 여부
    "is_deleted": "is_deleted",
    "deleted": "is_deleted",
    "status": "is_deleted",
    "del": "is_deleted",
    # 게시판
    "board": "board",
    "board_id": "board",
    "board_name": "board",
}


# ── SQL 파싱 ──────────────────────────────────────────────────────────────────

def _unquote_sql(s: str) -> str:
    """SQL 문자열 이스케이프 해제 ('...' 따옴표 제거 및 이스케이프 처리)."""
    if s == "NULL":
        return ""
    # 따옴표 제거
    if (s.startswith("'") and s.endswith("'")) or \
       (s.startswith('"') and s.endswith('"')):
        s = s[1:-1]
    # SQL 이스케이프 시퀀스 복원
    s = s.replace("\\'", "'").replace('\\"', '"')
    s = s.replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t")
    s = s.replace("\\\\", "\\")
    return s


def _tokenize_values(values_str: str) -> list[str]:
    """
    VALUES 절의 단일 행 '(...)'을 파싱하여 컬럼 값 리스트를 반환합니다.
    따옴표 안의 쉼표, 중첩 괄호를 올바르게 처리합니다.
    """
    # 앞뒤 괄호 제거
    s = values_str.strip()
    if s.startswith("("):
        s = s[1:]
    if s.endswith(")"):
        s = s[:-1]

    tokens: list[str] = []
    current = []
    in_string = False
    escape_next = False
    quote_char = None

    for ch in s:
        if escape_next:
            current.append(ch)
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            current.append(ch)
            continue
        if in_string:
            current.append(ch)
            if ch == quote_char:
                in_string = False
        else:
            if ch in ("'", '"'):
                in_string = True
                quote_char = ch
                current.append(ch)
            elif ch == ",":
                tokens.append("".join(current).strip())
                current = []
            else:
                current.append(ch)

    if current:
        tokens.append("".join(current).strip())

    return [_unquote_sql(t) for t in tokens]


def extract_table_names(sql_content: str) -> list[str]:
    """SQL 덤프에서 모든 테이블 이름을 추출합니다."""
    tables = set()
    # CREATE TABLE 패턴
    for m in re.finditer(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"]?(\w+)[`\"]?",
        sql_content,
        re.IGNORECASE,
    ):
        tables.add(m.group(1))
    # INSERT INTO 패턴
    for m in re.finditer(
        r"INSERT\s+INTO\s+[`\"]?(\w+)[`\"]?",
        sql_content,
        re.IGNORECASE,
    ):
        tables.add(m.group(1))
    return sorted(tables)


def is_bbs_table(name: str) -> bool:
    """테이블명이 BBS 관련 패턴과 일치하는지 확인합니다."""
    return any(pat.search(name) for pat in BBS_TABLE_PATTERNS)


def extract_create_columns(sql_content: str, table_name: str) -> list[str] | None:
    """
    CREATE TABLE 구문에서 컬럼명 목록을 추출합니다.
    반환: 컬럼명 리스트 (순서 보존) 또는 None (테이블 없음)
    """
    # CREATE TABLE 블록 찾기
    pattern = re.compile(
        rf"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"]?{re.escape(table_name)}[`\"]?\s*\((.*?)\)\s*(?:ENGINE|TYPE|DEFAULT|CHARSET|;)",
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.search(sql_content)
    if not m:
        return None

    block = m.group(1)
    columns = []
    for line in block.split("\n"):
        line = line.strip().rstrip(",")
        # PRIMARY KEY, KEY, INDEX, CONSTRAINT 줄 건너뜀
        if re.match(r"(?:PRIMARY\s+KEY|UNIQUE\s+KEY|KEY|INDEX|CONSTRAINT|CHECK)", line, re.I):
            continue
        # 컬럼 정의: `colname` TYPE ...
        col_m = re.match(r"[`\"]?(\w+)[`\"]?\s+\w", line)
        if col_m:
            columns.append(col_m.group(1).lower())

    return columns if columns else None


def parse_insert_rows(
    sql_content: str,
    table_name: str,
    columns: list[str],
) -> Iterator[dict[str, str]]:
    """
    INSERT INTO table_name VALUES (...), (...) 구문에서
    행 딕셔너리를 생성합니다.
    """
    # INSERT INTO 문 패턴 (multi-row VALUES 지원)
    insert_pattern = re.compile(
        rf"INSERT\s+INTO\s+[`\"]?{re.escape(table_name)}[`\"]?\s*"
        rf"(?:\([^)]+\)\s*)?VALUES\s*(.*?);",
        re.IGNORECASE | re.DOTALL,
    )

    for insert_m in insert_pattern.finditer(sql_content):
        values_block = insert_m.group(1).strip()

        # INSERT INTO tbl (col1, col2, ...) VALUES ... 형식에서 컬럼 추출
        col_override_m = re.search(
            rf"INSERT\s+INTO\s+[`\"]?{re.escape(table_name)}[`\"]?\s*\(([^)]+)\)\s*VALUES",
            insert_m.group(0),
            re.IGNORECASE,
        )
        if col_override_m:
            row_cols = [c.strip().strip("`\"'").lower() for c in col_override_m.group(1).split(",")]
        else:
            row_cols = columns

        # 각 (...)별로 행 파싱
        row_pattern = re.compile(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)")
        for row_m in row_pattern.finditer(values_block):
            values = _tokenize_values(row_m.group(0))
            if len(values) != len(row_cols):
                log.warning(
                    "컬럼 수 불일치: 테이블=%s 컬럼=%d 값=%d → 건너뜀",
                    table_name, len(row_cols), len(values),
                )
                continue
            yield dict(zip(row_cols, values))


def map_row_to_standard(raw_row: dict[str, str]) -> dict[str, str]:
    """
    BBS 테이블 행 → legacy_posts.csv 표준 컬럼으로 매핑합니다.
    """
    result = {"title": "", "content": "", "author": "", "created_at": "", "is_deleted": "0", "board": "general"}

    for src_col, value in raw_row.items():
        normalized = src_col.lower().strip()
        target = COLUMN_MAP.get(normalized)
        if target:
            if target == "is_deleted":
                # 상태값 정규화
                v = value.strip().lower()
                result["is_deleted"] = "1" if v in ("1", "true", "yes", "deleted", "삭제", "d", "n") else "0"
            elif target == "board":
                # board 값 정규화
                v = value.strip().lower()
                result["board"] = "visa" if "visa" in v or "비자" in v else "general"
            else:
                result[target] = value

    return result


# ── 메인 파서 ─────────────────────────────────────────────────────────────────

def parse_dump(
    sql_path: Path,
    target_table: str | None,
    encoding: str,
    dry_run: bool,
    board_override: str | None,
) -> list[dict[str, str]]:
    """
    SQL 덤프 파일 파싱 → 표준 행 리스트 반환.
    """
    log.info("=" * 62)
    log.info("parse_sql_dump  시작")
    log.info("  파일     : %s", sql_path)
    log.info("  인코딩   : %s", encoding)
    log.info("  테이블   : %s", target_table or "(자동 감지)")
    log.info("  모드     : %s", "DRY-RUN" if dry_run else "LIVE")
    log.info("=" * 62)

    # 파일 읽기 (인코딩 오류는 replace로 처리)
    try:
        sql_content = sql_path.read_text(encoding=encoding, errors="replace")
    except Exception as exc:
        raise SystemExit(f"[FATAL] SQL 파일 읽기 실패: {exc}")

    log.info("파일 크기: %.1f MB", len(sql_content) / 1_048_576)

    # 모든 테이블 추출
    all_tables = extract_table_names(sql_content)
    log.info("발견된 테이블: %d개", len(all_tables))

    # 테이블 결정
    if target_table:
        tables_to_process = [target_table]
    else:
        tables_to_process = [t for t in all_tables if is_bbs_table(t)]
        if not tables_to_process:
            log.warning("BBS 테이블을 자동 감지하지 못했습니다.")
            log.warning("--list-tables 로 전체 테이블 목록을 확인하고 --table 로 지정하세요.")
            log.info("모든 테이블: %s", ", ".join(all_tables[:20]))
            return []
        log.info("BBS 테이블 자동 감지: %s", ", ".join(tables_to_process))

    all_rows: list[dict[str, str]] = []

    for table in tables_to_process:
        # 컬럼 추출
        columns = extract_create_columns(sql_content, table)
        if not columns:
            log.warning("  [%s] CREATE TABLE 없음 → INSERT 컬럼 선언에서 추론", table)
            columns = []

        log.info("  [%s] 컬럼: %s", table, ", ".join(columns[:10]) + ("..." if len(columns) > 10 else ""))

        # 행 파싱
        row_count = 0
        for raw_row in parse_insert_rows(sql_content, table, columns):
            mapped = map_row_to_standard(raw_row)

            if not mapped["title"].strip():
                continue  # 빈 제목 건너뜀

            if board_override:
                mapped["board"] = board_override

            all_rows.append(mapped)
            row_count += 1

            if dry_run and row_count <= 3:
                log.info(
                    "  [DRY] title=%.50r  author=%.20r  date=%s  del=%s",
                    mapped["title"],
                    mapped["author"],
                    mapped["created_at"],
                    mapped["is_deleted"],
                )

        log.info("  [%s] 파싱 완료: %d행", table, row_count)

    log.info("=" * 62)
    log.info("총 파싱된 행: %d", len(all_rows))
    return all_rows


def save_csv(rows: list[dict[str, str]], out_path: Path) -> None:
    """표준 행 리스트 → legacy_posts.csv 저장."""
    fieldnames = ["title", "content", "author", "created_at", "is_deleted", "board"]
    with out_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    log.info("CSV 저장: %s  (%d행)", out_path, len(rows))


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cafe24 MySQL 덤프(.sql) → legacy_posts.csv 변환기"
    )
    parser.add_argument(
        "--sql",
        required=True,
        metavar="PATH",
        help="입력 SQL 덤프 파일 경로",
    )
    parser.add_argument(
        "--table",
        default=None,
        metavar="TABLE_NAME",
        help="파싱할 테이블명 (기본: BBS 패턴 자동 감지)",
    )
    parser.add_argument(
        "--out",
        default="legacy_posts.csv",
        metavar="PATH",
        help="출력 CSV 파일 경로 (기본: ./legacy_posts.csv)",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        metavar="ENC",
        help="SQL 파일 인코딩 (기본: utf-8, 한국: euc-kr 또는 cp949)",
    )
    parser.add_argument(
        "--board",
        choices=["general", "visa"],
        default=None,
        metavar="BOARD",
        help="모든 행의 board 강제 지정 (기본: 컬럼값 또는 general)",
    )
    parser.add_argument(
        "--list-tables",
        action="store_true",
        help="SQL 파일 내 테이블 목록만 출력하고 종료",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="파싱만 하고 CSV 저장하지 않음",
    )
    args = parser.parse_args()

    sql_path = Path(args.sql).resolve()
    if not sql_path.exists():
        raise SystemExit(f"[FATAL] SQL 파일 없음: {sql_path}")

    # --list-tables 모드
    if args.list_tables:
        sql_content = sql_path.read_text(encoding=args.encoding, errors="replace")
        tables = extract_table_names(sql_content)
        print(f"\n전체 테이블 ({len(tables)}개):")
        for t in tables:
            bbs_mark = " ← BBS 추정" if is_bbs_table(t) else ""
            print(f"  {t}{bbs_mark}")
        return

    rows = parse_dump(
        sql_path=sql_path,
        target_table=args.table,
        encoding=args.encoding,
        dry_run=args.dry_run,
        board_override=args.board,
    )

    if not rows:
        log.warning("변환된 행이 없습니다. --list-tables 로 테이블 목록을 확인하세요.")
        sys.exit(1)

    if args.dry_run:
        log.info("DRY-RUN 완료 — CSV 저장 건너뜀")
        log.info("실제 변환하려면 --dry-run 옵션 제거 후 재실행하세요.")
        return

    out_path = Path(args.out).resolve()
    save_csv(rows, out_path)

    log.info("")
    log.info("다음 단계: migrate_bbs.py 실행")
    log.info("  python backend/migrate_bbs.py --csv %s", out_path)


if __name__ == "__main__":
    main()
