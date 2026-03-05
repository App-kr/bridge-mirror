"""
jobs → client_inquiries 필드 보강 + memo 파싱
792건의 memo_extract 데이터를 jobs 테이블에서 보강
"""
import sqlite3
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DB_PATH = "master.db"


def parse_memo(memo):
    """memo 텍스트에서 구조화 데이터 추출."""
    if not memo:
        return {}
    result = {}

    # 급여: 2.3x, 2,4x, 270~, 2.80~3.00
    m = re.search(r"(?<!\d)(\d{1,2}[,.]\d{1,2})\s*[x~]", memo)
    if m:
        lo = m.group(1).replace(",", ".")
        try:
            if 1.5 <= float(lo) <= 5.0:
                result["salary_memo"] = f"{lo}m"
        except ValueError:
            pass

    # 숙소 관련
    housing_keywords = []
    if re.search(r"숙소|housing|furnished", memo, re.I):
        housing_keywords.append("숙소")
    if re.search(r"월세|rent", memo, re.I):
        housing_keywords.append("월세")
    if re.search(r"보증금|deposit", memo, re.I):
        housing_keywords.append("보증금")
    if housing_keywords:
        result["housing_memo"] = "/".join(housing_keywords)

    # 인원 수 (N명, N native)
    m = re.search(r"(\d+)\s*명", memo)
    if m:
        result["native_count_memo"] = m.group(1)

    # 식사
    if re.search(r"점심|식사|간식|meal|lunch", memo, re.I):
        result["meal_memo"] = "Y"

    # 직책 + 이름
    title_match = re.search(r"([\w가-힣]+)(원장|부원장|이사|대표|실장|부장|팀장)", memo)
    if title_match:
        name = title_match.group(1)
        title = title_match.group(2)
        # 너무 긴 이름은 학원명일 수 있으므로 필터
        if len(name) <= 5:
            result["contact_title"] = f"{name}{title}"

    return result


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row

    # jobs 데이터 로드 (internal_notes 기준)
    jobs_rows = conn.execute(
        "SELECT * FROM jobs WHERE internal_notes IS NOT NULL AND TRIM(internal_notes) <> ''"
    ).fetchall()
    jobs_by_notes = {}
    for j in jobs_rows:
        notes = j["internal_notes"]
        if notes not in jobs_by_notes:
            jobs_by_notes[notes] = dict(j)
    print(f"jobs 로드: {len(jobs_by_notes)}건 (unique internal_notes)")

    # client_inquiries memo_extract 그룹 로드
    inquiries = conn.execute(
        "SELECT * FROM client_inquiries WHERE source_file = 'memo_extract'"
    ).fetchall()
    print(f"memo_extract 대상: {len(inquiries)}건")

    # 보강 실행
    updated_jobs = 0
    updated_memo = 0
    skipped = 0

    # jobs → client_inquiries 필드 매핑
    FIELD_MAP = {
        "teaching_age": "teaching_age",
        "salary_raw": "salary_raw",
        "working_hours": "working_hours",
        "start_date": "start_date",
        "benefits": "benefits",
        "vacation": "vacation",
    }

    for row in inquiries:
        iid = row["id"]
        memo = row["memo"]
        updates = {}

        # 1) jobs 테이블 매칭
        if memo and memo in jobs_by_notes:
            j = jobs_by_notes[memo]
            for ci_col, job_col in FIELD_MAP.items():
                val = j.get(job_col)
                if val and str(val).strip() and str(val).strip() != "None":
                    # client_inquiries에 이미 값이 있으면 스킵
                    existing = row[ci_col] if ci_col in row.keys() else None
                    if not existing or str(existing).strip() in ("", "None"):
                        updates[ci_col] = str(val).strip()

            # housing은 jobs에서 housing_type으로 매핑
            housing_val = j.get("housing")
            if housing_val and str(housing_val).strip() and str(housing_val).strip() != "None":
                existing_ht = row["housing_type"] if "housing_type" in row.keys() else None
                if not existing_ht or str(existing_ht).strip() in ("", "None"):
                    updates["housing_type"] = str(housing_val).strip()

        # 2) memo 텍스트 파싱 (jobs 매칭 보완)
        parsed = parse_memo(memo)
        # contact_name 보강: 직책+이름
        if parsed.get("contact_title"):
            existing_cn = row["contact_name"] if "contact_name" in row.keys() else None
            if not existing_cn or str(existing_cn).strip() in ("", "None"):
                updates["contact_name"] = parsed["contact_title"]

        # meal 보강
        if parsed.get("meal_memo"):
            existing_meal = row["meal"] if "meal" in row.keys() else None
            if not existing_meal or str(existing_meal).strip() in ("", "None"):
                updates["meal"] = parsed["meal_memo"]

        if updates:
            set_parts = []
            vals = []
            for k, v in updates.items():
                set_parts.append(f"[{k}] = ?")
                vals.append(v)
            vals.append(iid)
            sql = f"UPDATE client_inquiries SET {', '.join(set_parts)} WHERE id = ?"
            conn.execute(sql, vals)

            if memo and memo in jobs_by_notes:
                updated_jobs += 1
            else:
                updated_memo += 1
        else:
            skipped += 1

    conn.commit()

    print(f"\n=== 보강 결과 ===")
    print(f"  jobs 매칭 보강: {updated_jobs}건")
    print(f"  memo 파싱 보강: {updated_memo}건")
    print(f"  스킵 (변경 없음): {skipped}건")

    # 결과 검증
    print(f"\n=== 보강 후 필드 현황 (전체 953건) ===")
    for col in [
        "teaching_age", "salary_raw", "working_hours", "start_date",
        "benefits", "vacation", "housing_type", "contact_name", "meal",
    ]:
        filled = conn.execute(
            f"SELECT COUNT(*) FROM client_inquiries WHERE [{col}] IS NOT NULL AND TRIM([{col}]) <> '' AND TRIM([{col}]) <> 'None'"
        ).fetchone()[0]
        before_pct = {
            "teaching_age": 15.6, "salary_raw": 15.5, "working_hours": 15.3,
            "start_date": 15.6, "benefits": 14.1, "vacation": 15.5,
            "housing_type": 15.4, "contact_name": 36.2, "meal": 14.9,
        }
        bp = before_pct.get(col, 0)
        pct = filled / 953 * 100
        delta = pct - bp
        print(f"  {col:20s}: {filled:>4d}/953 ({pct:5.1f}%) [+{delta:.1f}%]")

    conn.close()
    print("\n완료!")


if __name__ == "__main__":
    main()
