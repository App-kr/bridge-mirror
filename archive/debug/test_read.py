"""
test_read.py — Supabase 암호화 필드 복호화 검증

Supabase candidates 테이블에서 특정 구직자 1명을 읽어와
AES-256-GCM 암호화된 민감 필드를 복호화하여 출력합니다.

Usage:
    python -X utf8 test_read.py                        # 첫 번째 레코드
    python -X utf8 test_read.py --email user@email.com # 이메일로 지정
"""

import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

try:
    from supabase import create_client
except ImportError:
    print("[ERROR] supabase가 설치되지 않았습니다: pip install supabase")
    sys.exit(1)

try:
    from security_vault import decrypt_field, is_encrypted
except ImportError:
    print("[ERROR] security_vault.py를 찾을 수 없습니다.")
    sys.exit(1)

# 복호화 대상 필드
SENSITIVE_FIELDS = {
    "passport_status",
    "criminal_record",
    "health_info",
    "criminal_record_check",
}

SEP = "=" * 70


def get_client():
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise EnvironmentError("SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY가 .env에 없습니다.")
    return create_client(url, key)


def print_record(record: dict):
    email = record.get("email", "(이메일 없음)")
    name  = record.get("full_name", "(이름 없음)")

    print(f"\n{SEP}")
    print(f"  후보자: {name}  |  {email}")
    print(SEP)

    print("\n  [일반 필드]")
    normal_fields = [
        ("submitted_at",        "제출일시"),
        ("full_name",           "이름"),
        ("nationality",         "국적"),
        ("date_of_birth",       "생년월일"),
        ("gender",              "성별"),
        ("current_location",    "현재위치"),
        ("education",           "학력"),
        ("major",               "전공"),
        ("certification",       "자격증"),
        ("e_visa_status",       "E비자"),
        ("arc_status",          "ARC"),
        ("document_status",     "서류상태"),
        ("available_from",      "가능시작일"),
        ("experience",          "경력"),
        ("current_salary",      "현재급여"),
        ("desired_salary",      "희망급여"),
        ("mobile_phone",        "전화번호"),
    ]
    for col, label in normal_fields:
        val = record.get(col) or "(null)"
        print(f"    {label:<14} : {val}")

    print("\n  [암호화 필드 - 복호화 결과]")
    all_ok = True
    for field in sorted(SENSITIVE_FIELDS):
        raw = record.get(field)
        if not raw:
            print(f"    {field:<28} : (null)")
            continue

        if is_encrypted(raw):
            try:
                plaintext = decrypt_field(raw)
                print(f"    {field:<28} : {plaintext}  [복호화 OK]")
            except Exception as exc:
                print(f"    {field:<28} : [복호화 실패] {exc}")
                all_ok = False
        else:
            print(f"    {field:<28} : {raw}  [암호화되지 않음]")

    print(f"\n  암호화 필드 복호화: {'전체 성공' if all_ok else '일부 실패'}")
    print(SEP + "\n")


def main():
    parser = argparse.ArgumentParser(description="Supabase 암호화 필드 복호화 테스트")
    parser.add_argument("--email", type=str, default=None,
                        help="조회할 후보자 이메일 (미입력시 첫 번째 레코드)")
    args = parser.parse_args()

    print(f"\n{SEP}")
    print("  Bridge Base - 복호화 검증 테스트")
    print(SEP)

    client = get_client()

    if args.email:
        print(f"\n  조회 중: email = {args.email}")
        res = client.table("candidates").select("*").eq("email", args.email).limit(1).execute()
    else:
        print("\n  조회 중: 첫 번째 레코드")
        res = client.table("candidates").select("*").limit(1).execute()

    if not res.data:
        print("  [결과 없음] 해당 조건의 레코드를 찾을 수 없습니다.")
        sys.exit(0)

    record = res.data[0]
    print_record(record)


if __name__ == "__main__":
    main()
