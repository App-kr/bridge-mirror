"""One-time migration: populate salary_raw + employer_display_name from raw_text/internal_notes."""
import sqlite3
import re
import sys

DB = "Q:/Claudework/bridge base/master.db"

_TITLES = ["원장","부원장","대표","이사","부장","실장","팀장","담당","선생","매니저","관장","사장"]
_LOCATIONS = [
    "서울","부산","대구","인천","광주","대전","울산","세종",
    "경기","강원","충북","충남","전북","전남","경북","경남","제주",
    "해운대","동래","사직","고양","일산","수지","용인","기흥",
    "송도","화성","남동탄","동탄","분당","성남","수원","안양",
    "의정부","구로","강남","마포","잠실","종로","신촌","홍대",
    "부천","광명","시흥","안산","군포","의왕","평택","파주",
    "김포","양주","구미","포항","경산","창원","청주","천안",
    "아산","전주","순천","여수","목포","서귀포",
]


def parse_name_from_memo(memo):
    """Extract company name from memo (same logic as backend _parse_memo_pii)."""
    if not memo:
        return ""
    full = memo.strip()
    inner = full
    mp = re.match(r"^\((.+)\)\s*$", inner, re.S)
    if not mp:
        mp = re.match(r"^\((.+?)\)", inner, re.S)
    if not mp:
        mp = re.match(r"^\((.+)", inner, re.S)
    if mp:
        inner = mp.group(1).strip()
    name_src = inner
    changed = True
    while changed:
        changed = False
        for loc in _LOCATIONS:
            m = re.match("^" + re.escape(loc) + r"\s*", name_src)
            if m:
                name_src = name_src[m.end():]
                changed = True
                break
    title_pat = "|".join(re.escape(t) for t in _TITLES)
    stop = re.search(
        r"(01[016789][-\s]?\d|[A-Za-z0-9._%+-]+@|" + title_pat + ")",
        name_src,
    )
    if stop:
        candidate = name_src[: stop.start()].strip().rstrip("/ ,;")
        if candidate and len(candidate) <= 30:
            return candidate
    return ""


def get_memo_for_pii(internal_notes, raw_text):
    """Get memo text for PII parsing (with raw_text tail fallback)."""
    memo = internal_notes or ""
    if not memo:
        raw = raw_text or ""
        # Try parenthetical block at end
        tail = re.search(r'\([^)]{10,}\)\s*["\x27`]*\s*$', raw)
        if not tail:
            tail = re.search(r"\(.{10,}$", raw)
        if tail:
            memo = tail.group(0)
    return memo


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # --- Fix 1: salary_raw from raw_text ---
    rows = conn.execute(
        "SELECT id, raw_text FROM jobs "
        "WHERE (salary_raw IS NULL OR salary_raw='') "
        "AND raw_text IS NOT NULL AND raw_text!='' AND is_deleted=0"
    ).fetchall()
    sal_updated = 0
    for r in rows:
        m = re.search(r"Monthly Salary\s*:\s*(.+)", r["raw_text"])
        if m:
            sal = m.group(1).strip().strip('`"')
            conn.execute("UPDATE jobs SET salary_raw=? WHERE id=?", (sal, r["id"]))
            print(f"  salary  ID={r['id']}: <- {sal!r}")
            sal_updated += 1
        else:
            m2 = re.search(r"(Hourly wage[^\n]+|salary\s+negotiable[^\n]*)", r["raw_text"], re.I)
            if m2:
                sal = m2.group(1).strip().strip('`"')
                conn.execute("UPDATE jobs SET salary_raw=? WHERE id=?", (sal, r["id"]))
                print(f"  salary  ID={r['id']}: <- {sal!r}")
                sal_updated += 1
            else:
                print(f"  salary  ID={r['id']}: no pattern found")

    # --- Fix 2: employer_display_name from memo ---
    rows2 = conn.execute(
        "SELECT id, internal_notes, raw_text FROM jobs "
        "WHERE (employer_display_name IS NULL OR employer_display_name='') AND is_deleted=0"
    ).fetchall()
    name_updated = 0
    for r in rows2:
        memo = get_memo_for_pii(r["internal_notes"], r["raw_text"])
        name = parse_name_from_memo(memo)
        if name:
            conn.execute(
                "UPDATE jobs SET employer_display_name=? WHERE id=?", (name, r["id"])
            )
            name_updated += 1

    conn.commit()

    # --- Verify ---
    still_null_sal = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE (salary_raw IS NULL OR salary_raw='') AND is_deleted=0"
    ).fetchone()[0]
    still_null_name = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE (employer_display_name IS NULL OR employer_display_name='') AND is_deleted=0"
    ).fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_deleted=0").fetchone()[0]

    print(f"\n=== Results ===")
    print(f"salary_raw: updated {sal_updated}, still empty {still_null_sal}/{total}")
    print(f"employer_display_name: updated {name_updated}/{len(rows2)}, still empty {still_null_name}/{total}")

    conn.close()


if __name__ == "__main__":
    main()
