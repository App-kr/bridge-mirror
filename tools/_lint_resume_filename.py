#!/usr/bin/env python3
"""
Lint rule (v2.0): 이력서 파일명 하드코딩 금지.
_build_output_filename() SSoT 외 파일명 생성 패턴 탐지.

사용:
  python tools/_lint_resume_filename.py      # 전체 검사
  python tools/_lint_resume_filename.py api_server.py  # 단일 파일

Exit:
  0 — 위반 없음
  1 — 위반 발견 (pre-commit/CI 에서 차단)
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# 금지 패턴 (하드코딩 이력서 파일명)
FORBIDDEN_PATTERNS = [
    (r'["\']BRJ\d+_resume\.pdf["\']', 'BRJ{num}_resume.pdf 하드코딩 — _build_output_filename 사용'),
    (r'["\']\d+_resume\.pdf["\']',    '{num}_resume.pdf 하드코딩 — _build_output_filename 사용'),
    (r'["\']resume\.pdf["\']',        'resume.pdf 하드코딩 — _build_output_filename 사용'),
    (r'f["\'].*\{.*sheet_number.*\}.*_resume\.pdf["\']', 'f-string 파일명 — _build_output_filename 사용'),
]

# 검사 대상 — 이력서 파이프라인 관련 파일
TARGETS = [
    'api_server.py',
    'tools/doc_processor.py',
    'web_frontend/src/app/admin/resume-converter/page.tsx',
    'web_frontend/src/app/admin/introduce-mail/page.tsx',
]

# 예외: _build_output_filename 함수 정의 자체는 제외
EXEMPT_LINES = [
    'def _build_output_filename',
    'filename=encode_rfc2231',  # RFC 5987 처리
]


def scan_file(fpath: Path) -> list[str]:
    if not fpath.exists():
        return []
    violations = []
    try:
        lines = fpath.read_text(encoding='utf-8', errors='ignore').splitlines()
    except Exception:
        return []
    for i, line in enumerate(lines, 1):
        # 주석 라인 제외
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('*'):
            continue
        # 예외 라인 제외
        if any(ex in line for ex in EXEMPT_LINES):
            continue
        for pattern, msg in FORBIDDEN_PATTERNS:
            if re.search(pattern, line):
                violations.append(f"{fpath.relative_to(BASE)}:{i}: {msg}\n    >> {line.strip()[:120]}")
    return violations


def main(argv: list[str]) -> int:
    targets = argv[1:] if len(argv) > 1 else TARGETS
    all_violations: list[str] = []
    for t in targets:
        p = BASE / t if not Path(t).is_absolute() else Path(t)
        all_violations.extend(scan_file(p))

    if all_violations:
        print("[LINT] 이력서 파일명 하드코딩 위반 발견:")
        for v in all_violations:
            print(f"  {v}")
        print(f"\n총 {len(all_violations)}건 — _build_output_filename() 사용 필수")
        return 1
    print("[LINT] 이력서 파일명 규격 OK (위반 없음)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
