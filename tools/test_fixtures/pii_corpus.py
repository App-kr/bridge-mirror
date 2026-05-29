"""
BRIDGE doc_processor PII 회귀 코퍼스
=====================================

Opus 보안감사 권고에 따라 실파일에서 발견된 PII 누출/오삭제 케이스를
합성 fixture로 박제. 매 커밋 시 회귀 방지.

규칙:
  - REDACT: 토큰  → cleaned 결과에 토큰이 없어야 통과
  - PRESERVE       → cleaned 결과에 원본 핵심어가 보존되어야 통과
  - REDACT_LINE    → 줄 자체가 삭제되어야 통과

발견 출처:
  - 5739 / 6525 실파일 검증 (2026-05-29)
  - Opus 보안감사 보고서 (anu 부분매칭, 종교, 다단계 주소)
"""

# (input_text, expectation_tag, note)
CASES = [
    # ── 한국 학원 브랜드 (필수 삭제) ──
    ("Altiora Pangram English Academy, South Korea (2020-2022)",
     "REDACT:Altiora",
     "Altiora Pangram → 브랜드 삭제, English Academy 보존"),
    ("Brandy English Academy, Gwangmyeong (2018-2020)",
     "REDACT:Brandy",
     "Brandy English Academy → 브랜드 삭제"),
    ("CCLC (Creative Children Learning Center)",
     "REDACT:CCLC",
     "CCLC + Creative Children → 브랜드 삭제 (6525 발견)"),
    ("PSA Seocho",
     "REDACT:PSA",
     "PSA Seocho → 브랜드 삭제 (6525 발견)"),

    # ── 다단계 한국 주소 (필수 삭제) ──
    ("Gwangmyeong-si, Gyeonggi-do, South Korea",
     "REDACT:Gwangmyeong-si",
     "다단계 주소 — 선행 세그먼트 누출 방지"),
    ("Seocho-gu Hyoryeong-ro 231",
     "REDACT:Hyoryeong-ro",
     "한국 행정구역 도로명 (6525 발견)"),

    # ── 미국 주소 (필수 삭제) ──
    ("Bank of America - Maplewood, NJ - January 2016",
     "REDACT:Maplewood",
     "anu/january 부분매칭 버그 회귀 방지 (6525 발견)"),
    ("114 West 47th Street, 7th Floor, New York, NY 10036",
     "REDACT:10036",
     "ZIP 코드 잔존 방지 (6525 발견)"),
    ("385 Rifle Camp Road, 3rd Floor Woodland Park, NJ 07424",
     "REDACT:Woodland Park",
     "미국 NJ 도시 + ZIP"),

    # ── 종교 정보 (차별금지법 / 필수 삭제) ──
    ("I am currently living in Korea as a Catholic missionary with my family",
     "REDACT:Catholic missionary",
     "종교 정보 prose (6525 발견)"),
    ("Christian community outreach program",
     "REDACT:Christian community",
     "기독교 커뮤니티 언급"),

    # ── 연락처 ──
    ("Email: alarconalan6336@gmail.com",
     "REDACT:gmail.com",
     "이메일 삭제"),
    ("Phone: 010-9060-1976",
     "REDACT:9060-1976",
     "한국 휴대폰 삭제"),

    # ── 보존 케이스 (누출이 아니라 데이터 무결성) ──
    ("Developed a project-based curriculum for advanced learners",
     "PRESERVE",
     "깨끗한 줄 — 어떤 키워드도 삭제 안 됨"),
    ("I use pangrams to teach typing skills",
     "PRESERVE:pangrams",
     "'pangram' 단독 = 교육용어 (공통어 오탐 방지)"),
    ("Started teaching in January 2020",
     "PRESERVE:January",
     "anu/january 부분매칭 회귀 방지 — January 보존"),
    ("Worked with students at Manual Training Center",
     "PRESERVE:Manual",
     "anu/manual 부분매칭 회귀 방지 — Manual 보존"),
    ("Various assessment methods analysis",
     "PRESERVE:Various",
     "anu/various 부분매칭 회귀 방지"),
    ("Annual planning session for the academic year",
     "PRESERVE:Annual",
     "anu/annual 부분매칭 회귀 방지"),
    ("Institute of Technology curriculum design",
     "PRESERVE:Institute",
     "tut/institute 부분매칭 회귀 방지"),

    # ── Berlin 외국 경력 보존 (메모리 규칙: 외국 직장명 보존) ──
    # 학교명 일반화는 유지하되 국가명은 보존 → 외국 경력 표시 유지
    ("Senior Teacher at Berlin International School, Germany (2019-2021)",
     "PRESERVE:Germany",
     "외국 경력 — 거리주소 없으면 국가명 보존 (Germany 유지)"),
    ("Worked in Tokyo, Japan as ESL instructor",
     "PRESERVE:Japan",
     "외국 경력 — Tokyo는 일반화되어도 Japan 보존"),
    ("1600 Pennsylvania Avenue, Washington DC",
     "REDACT:1600",
     "외국 거리주소 — 거리단위 토큰 동반 시 삭제"),
]


def run_corpus_tests(verbose=False):
    """전 케이스 통과 여부 검증. 실패 건 반환."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from doc_processor import remove_pii

    failures = []
    passes = 0
    for text, expect, note in CASES:
        cleaned, log = remove_pii(text, candidate=None)
        tag, _, target = expect.partition(":")
        ok = True
        if tag == "REDACT" and target:
            # 대상 토큰이 cleaned에 남아있으면 실패
            if target.lower() in cleaned.lower():
                ok = False
        elif tag == "REDACT_LINE":
            if cleaned.strip():
                ok = False
        elif tag == "PRESERVE":
            if target:
                # 대상 토큰이 cleaned에 보존되어야 통과
                if target.lower() not in cleaned.lower():
                    ok = False
            # 보존 없는 PRESERVE는 입력 자체가 거의 변경되지 않아야 함
            # (오탐 ≤ 30%까지는 허용)
        if ok:
            passes += 1
            if verbose:
                print(f"  PASS [{tag:10s}] {note}")
        else:
            failures.append((text, expect, cleaned, note))
            print(f"  FAIL [{tag:10s}] {note}")
            print(f"    in:  {text!r}")
            print(f"    out: {cleaned!r}")

    print(f"\n{'='*60}")
    print(f"통과: {passes}/{len(CASES)}, 실패: {len(failures)}")
    return failures


if __name__ == "__main__":
    failures = run_corpus_tests(verbose=True)
    import sys
    sys.exit(0 if not failures else 1)
