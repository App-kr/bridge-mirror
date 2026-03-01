"""
parse_gnuboard.py — coreabridge3 그누보드5 덤프 → legacy_posts.csv
"""
import re
import csv
from pathlib import Path

DUMP = Path("Q:/Claudework/bridge base/coreabridge3-20260224.dump")
OUT  = Path("Q:/Claudework/bridge base/legacy_posts.csv")

TABLE_BOARD = {
    "g5_write_jobboard":       "general",
    "g5_write_review":         "general",
    "g5_write_support":        "general",
    "g5_write_support_korean": "general",
    "g5_write_visa":           "visa",
    "g5_write_apply":          "general",
    "g5_write_recruiting":     "general",
}

def unquote(s: str) -> str:
    s = s.strip()
    if s == "NULL":
        return ""
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        s = s[1:-1]
    s = s.replace("\\'", "'")
    s = s.replace("\\n", "\n")
    s = s.replace("\\r", "")
    s = s.replace("\\t", "\t")
    s = s.replace("\\\\", "\\")
    return s

def split_values(vals: str) -> list:
    """Splits a VALUES row string into individual field tokens."""
    parts = []
    cur = []
    inq = False
    esc = False
    qc = None
    for ch in vals:
        if esc:
            cur.append(ch)
            esc = False
            continue
        if ch == "\\":
            esc = True
            cur.append(ch)
            continue
        if inq:
            cur.append(ch)
            if ch == qc:
                inq = False
        else:
            if ch in ("'", '"'):
                inq = True
                qc = ch
                cur.append(ch)
            elif ch == ",":
                parts.append("".join(cur).strip())
                cur = []
            else:
                cur.append(ch)
    if cur:
        parts.append("".join(cur).strip())
    return parts

def main():
    print(f"읽는 중: {DUMP} ({DUMP.stat().st_size // 1024 // 1024}MB)")
    content = DUMP.read_text(encoding="utf-8", errors="replace")

    all_rows = []

    for table, board in TABLE_BOARD.items():
        # 테이블 컬럼 순서 파악
        col_m = re.search(
            rf"CREATE TABLE `{table}` \((.*?)\) ENGINE",
            content, re.DOTALL
        )
        if not col_m:
            print(f"  [{table}] 테이블 없음 — 건너뜀")
            continue
        columns = re.findall(r"`(\w+)`", col_m.group(1))

        # 컬럼 인덱스 매핑
        try:
            idx_is_comment = columns.index("wr_is_comment")
            idx_subject    = columns.index("wr_subject")
            idx_content    = columns.index("wr_content")
        except ValueError:
            print(f"  [{table}] 필수 컬럼 없음 — 건너뜀")
            continue

        idx_name     = columns.index("wr_name")     if "wr_name"     in columns else None
        idx_datetime = columns.index("wr_datetime") if "wr_datetime" in columns else None
        idx_option   = columns.index("wr_option")   if "wr_option"   in columns else None

        count = 0
        inserts = re.findall(
            rf"INSERT INTO `{table}` VALUES\s*(.*?);",
            content, re.DOTALL
        )
        for block in inserts:
            for m in re.finditer(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)", block):
                parts = split_values(m.group(1))
                if len(parts) <= max(idx_subject, idx_content, idx_is_comment):
                    continue

                if unquote(parts[idx_is_comment]) != "0":
                    continue  # 댓글 제외, 원글만

                title   = unquote(parts[idx_subject]).strip()
                content_body = unquote(parts[idx_content]).strip()
                if not title:
                    continue

                author     = unquote(parts[idx_name])     if (idx_name     is not None and idx_name     < len(parts)) else ""
                created_at = unquote(parts[idx_datetime]) if (idx_datetime is not None and idx_datetime < len(parts)) else ""

                # wr_option에 'secret' 있으면 is_deleted=1로 처리
                option_val = unquote(parts[idx_option]) if (idx_option is not None and idx_option < len(parts)) else ""
                is_deleted = "1" if "secret" in option_val else "0"

                all_rows.append({
                    "board":      board,
                    "title":      title,
                    "content":    content_body,
                    "author":     author,
                    "created_at": created_at,
                    "is_deleted": is_deleted,
                })
                count += 1

        print(f"  [{table}] {count}개 원글 추출 (board={board})")

    # CSV 저장
    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["board", "title", "content", "author", "created_at", "is_deleted"]
        )
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n총 {len(all_rows)}개 행 → {OUT}")
    print("다음 단계: python backend/migrate_bbs.py --csv legacy_posts.csv")

if __name__ == "__main__":
    main()
