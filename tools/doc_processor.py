"""
BRIDGE Document Processor v1.0
후보자 이력서/커버레터에서 PII 삭제 + 강사번호 입력

사용법:
  python doc_processor.py process <입력폴더> [--output <출력폴더>]
  python doc_processor.py process <단일파일> --number 1065
  python doc_processor.py lookup <이름 또는 이메일>

예시:
  python doc_processor.py process "Q:/Work place/incoming"
  python doc_processor.py process "resume.docx" --number 3057
  python doc_processor.py lookup "Tahliso Makaleng"

지원 형식: .docx, .pdf (PDF는 텍스트 추출→DOCX 재생성)
"""

import argparse
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# ── 설정 ──────────────────────────────────────────────
DB_PATH = Path("Q:/Claudework/bridge base/master.db")
DEFAULT_OUTPUT = Path("Q:/Claudework/bridge base/tools/processed_docs")
BACKUP_DIR = Path("Q:/Claudework/bridge base/tools/processed_docs/originals")

# ── PII 패턴 ──────────────────────────────────────────
# 이메일
RE_EMAIL = re.compile(
    r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b'
)

# 전화번호 (국제/국내 다양한 형식)
RE_PHONE = re.compile(
    r'(?:\+?\d{1,3}[\s\-.]?)?\(?\d{2,4}\)?[\s\-.]?\d{3,4}[\s\-.]?\d{3,4}\b'
)

# URL (http/https/www)
RE_URL = re.compile(
    r'https?://[^\s<>\"\']+|www\.[^\s<>\"\']+',
    re.IGNORECASE
)

# LinkedIn 프로필
RE_LINKEDIN = re.compile(
    r'(?:linkedin\.com/in/[^\s<>\"\']+|linkedin\s*:?\s*[^\s,;\n]+)',
    re.IGNORECASE
)

# 카카오톡 ID
RE_KAKAO = re.compile(
    r'(?:kakao(?:talk)?|카카오(?:톡)?)\s*:?\s*[A-Za-z0-9._\-]+',
    re.IGNORECASE
)

# SNS (Instagram, Facebook, Twitter, WhatsApp, Line, WeChat, Skype)
RE_SNS = re.compile(
    r'(?:instagram|facebook|twitter|whatsapp|line|wechat|skype|telegram)\s*:?\s*[@]?[A-Za-z0-9._\-]+',
    re.IGNORECASE
)

# 한국 주소 패턴 (시/도/구/동/로 포함)
RE_KR_ADDRESS = re.compile(
    r'(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)'
    r'(?:특별시|광역시|도|특별자치시|특별자치도)?'
    r'[\s]?(?:\S+(?:시|군|구|읍|면|동|리|로|길|번지)[\s]?){0,5}',
    re.UNICODE
)

# 여권번호 패턴
RE_PASSPORT = re.compile(
    r'\b[A-Z]{1,2}\d{7,8}\b'
)

# 한국 거주 관련 키워드
KR_LOCATION_KEYWORDS = [
    'korea', 'seoul', 'busan', 'daegu', 'incheon', 'gwangju',
    'daejeon', 'ulsan', 'sejong', 'gyeonggi', 'gangwon',
    'chungbuk', 'chungnam', 'jeonbuk', 'jeonnam',
    'gyeongbuk', 'gyeongnam', 'jeju',
    'south korea', 'republic of korea', 'rok',
    '한국', '서울', '부산', '대구', '인천', '광주', '대전', '울산',
    '세종', '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주',
    'suwon', 'seongnam', 'goyang', 'yongin', 'changwon',
    'ansan', 'anyang', 'namyangju', 'hwaseong', 'pyeongtaek',
    'gimpo', 'gwacheon', 'uijeongbu', 'paju', 'yangju',
    'pocheon', 'dongducheon', 'guri', 'hanam', 'icheon',
    'osan', 'gunpo', 'uiwang', 'siheung', 'bucheon',
    'jeonju', 'cheongju', 'cheonan', 'asan',
    'gimhae', 'yangsan', 'geoje', 'tongyeong',
    'mokpo', 'yeosu', 'suncheon', 'gwangyang',
    'gyeongju', 'pohang', 'andong', 'gumi',
    'chuncheon', 'wonju', 'gangneung', 'sokcho',
    'itaewon', 'gangnam', 'hongdae', 'sinchon', 'mapo',
    'jamsil', 'songpa', 'yongsan', 'nowon', 'bundang',
    'ilsan', 'dongtan', 'pangyo',
]

# 거주지/위치 관련 라벨
LOCATION_LABELS = [
    'current location', 'current address', 'address', 'location',
    'residence', 'residing', 'living in', 'based in',
    'city', 'province', 'country of residence',
    '현재 위치', '거주지', '주소', '현위치',
]

# 직장명 관련 라벨 (교육기관 institution/university 제외)
WORKPLACE_LABELS = [
    'current employer', 'employer', 'company', 'workplace',
    'school name', 'academy name', 'hagwon',
    '현 직장', '근무지', '학원명', '학교명',
]

# PII 라벨 (해당 줄 전체 삭제)
PII_LINE_LABELS = [
    'email', 'e-mail', 'phone', 'telephone', 'tel', 'mobile',
    'cell', 'contact', 'kakao', 'kakaotalk', 'line', 'skype',
    'whatsapp', 'wechat', 'telegram', 'instagram', 'facebook',
    'twitter', 'linkedin', 'website', 'personal website',
    'passport', 'passport number', 'passport no',
    '이메일', '전화', '연락처', '카카오', '여권',
]


def connect_db():
    """master.db 연결"""
    if not DB_PATH.exists():
        print(f"[ERROR] DB not found: {DB_PATH}")
        sys.exit(1)
    return sqlite3.connect(str(DB_PATH))


def lookup_candidate(query: str):
    """이름 또는 이메일로 후보자 검색 → (sheet_number, full_name, nationality, email)"""
    conn = connect_db()
    c = conn.cursor()

    # 이메일로 검색
    if '@' in query:
        c.execute(
            "SELECT sheet_number, full_name, nationality, email "
            "FROM candidates WHERE email LIKE ? LIMIT 5",
            (f"%{query}%",)
        )
    else:
        # 이름으로 검색
        c.execute(
            "SELECT sheet_number, full_name, nationality, email "
            "FROM candidates WHERE full_name LIKE ? LIMIT 10",
            (f"%{query}%",)
        )

    results = c.fetchall()
    conn.close()
    return results


def get_candidate_by_number(number: int):
    """sheet_number로 후보자 조회"""
    conn = connect_db()
    c = conn.cursor()
    c.execute(
        "SELECT sheet_number, full_name, nationality, email, "
        "mobile_phone, kakaotalk, current_location "
        "FROM candidates WHERE sheet_number = ?",
        (number,)
    )
    row = c.fetchone()
    conn.close()
    return row


def is_korea_location(text: str) -> bool:
    """텍스트가 한국 내 위치인지 판별"""
    lower = text.lower().strip()
    for kw in KR_LOCATION_KEYWORDS:
        if kw in lower:
            return True
    return False


def remove_pii_from_text(text: str, candidate_name: str = None) -> str:
    """텍스트에서 PII 삭제"""
    # 줄 단위 처리 (PII 라벨이 있는 줄은 전체 삭제)
    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        stripped = line.strip().lower()

        # PII 라벨로 시작하는 줄 → 전체 삭제
        skip = False
        for label in PII_LINE_LABELS:
            if stripped.startswith(label) and (
                len(stripped) == len(label)
                or stripped[len(label):].lstrip().startswith(':')
                or stripped[len(label):].lstrip().startswith(' ')
            ):
                skip = True
                break
        if skip:
            continue

        cleaned_lines.append(line)

    result = '\n'.join(cleaned_lines)

    # 1) 여권번호 삭제 (전화번호보다 먼저 — 숫자 패턴 충돌 방지)
    result = RE_PASSPORT.sub('', result)

    # 2) 이메일 삭제
    result = RE_EMAIL.sub('', result)

    # 3) LinkedIn 삭제
    result = RE_LINKEDIN.sub('', result)

    # 4) 카카오톡 삭제
    result = RE_KAKAO.sub('', result)

    # 5) SNS 삭제
    result = RE_SNS.sub('', result)

    # 6) URL 삭제
    result = RE_URL.sub('', result)

    # 7) 전화번호 삭제 (7자리 이상)
    def phone_replacer(m):
        digits = re.sub(r'\D', '', m.group())
        if len(digits) >= 7:
            return ''
        return m.group()
    result = RE_PHONE.sub(phone_replacer, result)

    # 8) 한국 주소 → "Korea" 변환
    result = RE_KR_ADDRESS.sub('Korea', result)

    # 9) 후보자 이름 삭제 (DB에서 가져온 풀네임)
    if candidate_name:
        for variant in _name_variants(candidate_name):
            result = re.sub(re.escape(variant), '', result, flags=re.IGNORECASE)

    # 10) 위치/거주지 라벨 뒤의 값이 한국이면 "Korea"로 변환
    for label in LOCATION_LABELS:
        pattern = re.compile(
            rf'({re.escape(label)}\s*:?\s*)(.+)',
            re.IGNORECASE
        )
        def loc_replacer(m):
            prefix = m.group(1)
            value = m.group(2).strip()
            if is_korea_location(value):
                return f"{prefix}Korea"
            return m.group(0)
        result = pattern.sub(loc_replacer, result)

    # 11) 직장명 라벨 뒤의 값 삭제
    for label in WORKPLACE_LABELS:
        pattern = re.compile(
            rf'({re.escape(label)}\s*:?\s*)(.+)',
            re.IGNORECASE
        )
        result = pattern.sub(r'\1', result)

    # 연속 빈줄 정리
    result = re.sub(r'\n{3,}', '\n\n', result)

    return result


def _name_variants(full_name: str) -> list:
    """이름 변형 생성 (풀네임, First Last, Last First 등)"""
    parts = full_name.strip().split()
    if not parts:
        return []

    variants = [full_name.strip()]

    # 세미콜론이나 괄호로 분리된 별명 처리
    # e.g., "Jashen Arianne Paler Alaba ; Shen"
    if ';' in full_name:
        main_name = full_name.split(';')[0].strip()
        nickname = full_name.split(';')[1].strip()
        variants.append(main_name)
        if nickname:
            variants.append(nickname)
        parts = main_name.split()

    if '(' in full_name:
        main_name = re.sub(r'\s*\([^)]*\)', '', full_name).strip()
        nickname = re.search(r'\(([^)]+)\)', full_name)
        variants.append(main_name)
        if nickname:
            variants.append(nickname.group(1))
        parts = main_name.split()

    if len(parts) >= 2:
        variants.append(f"{parts[0]} {parts[-1]}")  # First Last
        variants.append(f"{parts[-1]}, {parts[0]}")  # Last, First
        variants.append(f"{parts[-1]} {parts[0]}")   # Last First
        variants.append(parts[0])  # First name only
        variants.append(parts[-1])  # Last name only

    return list(set(v for v in variants if len(v) > 1))


def process_docx(filepath: Path, brj_number: int, candidate_name: str = None) -> Path:
    """DOCX 파일 처리: PII 삭제 + 번호 삽입"""
    import docx

    doc = docx.Document(str(filepath))

    # 1) 모든 단락에서 PII 삭제
    for para in doc.paragraphs:
        original = para.text
        cleaned = remove_pii_from_text(original, candidate_name)
        if cleaned != original:
            # 단락의 모든 run 텍스트를 교체
            # 단순 방식: 첫 run에 전체 텍스트, 나머지 run 비우기
            if para.runs:
                # 기존 서식 보존하면서 텍스트만 교체
                full_original = ''.join(r.text for r in para.runs)
                if full_original == original:
                    para.runs[0].text = cleaned
                    for run in para.runs[1:]:
                        run.text = ''
                else:
                    # 복잡한 경우: 전체 교체
                    para.runs[0].text = cleaned
                    for run in para.runs[1:]:
                        run.text = ''

    # 2) 테이블 내 PII 삭제
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    original = para.text
                    cleaned = remove_pii_from_text(original, candidate_name)
                    if cleaned != original and para.runs:
                        para.runs[0].text = cleaned
                        for run in para.runs[1:]:
                            run.text = ''

    # 3) 헤더/푸터 PII 삭제
    for section in doc.sections:
        for header in [section.header, section.first_page_header]:
            if header and header.paragraphs:
                for para in header.paragraphs:
                    original = para.text
                    cleaned = remove_pii_from_text(original, candidate_name)
                    if cleaned != original and para.runs:
                        para.runs[0].text = cleaned
                        for run in para.runs[1:]:
                            run.text = ''
        for footer in [section.footer, section.first_page_footer]:
            if footer and footer.paragraphs:
                for para in footer.paragraphs:
                    original = para.text
                    cleaned = remove_pii_from_text(original, candidate_name)
                    if cleaned != original and para.runs:
                        para.runs[0].text = cleaned
                        for run in para.runs[1:]:
                            run.text = ''

    # 4) 문서 최상단에 BRJ 번호 삽입
    # 첫 단락 앞에 새 단락 추가
    first_para = doc.paragraphs[0] if doc.paragraphs else None
    if first_para:
        new_para = first_para.insert_paragraph_before(str(brj_number))
        run = new_para.runs[0]
        run.bold = True
        run.font.size = docx.shared.Pt(18)
    else:
        p = doc.add_paragraph(str(brj_number))
        p.runs[0].bold = True
        p.runs[0].font.size = docx.shared.Pt(18)

    return doc


def process_pdf(filepath: Path, brj_number: int, candidate_name: str = None) -> str:
    """PDF 파일에서 텍스트 추출 + PII 삭제 → 정리된 텍스트 반환"""
    import fitz  # PyMuPDF

    doc = fitz.open(str(filepath))
    all_text = []

    for page in doc:
        text = page.get_text()
        cleaned = remove_pii_from_text(text, candidate_name)
        all_text.append(cleaned)

    doc.close()

    # BRJ 번호를 최상단에 추가
    header = f"{brj_number}\n{'=' * 40}\n\n"
    return header + '\n--- PAGE BREAK ---\n'.join(all_text)


def save_processed_docx(doc, original_path: Path, brj_number: int, output_dir: Path):
    """처리된 DOCX 저장"""
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = original_path.stem
    out_name = f"BRJ{brj_number}_{stem}.docx"
    out_path = output_dir / out_name
    doc.save(str(out_path))
    return out_path


def save_processed_pdf_as_txt(text: str, original_path: Path, brj_number: int, output_dir: Path):
    """처리된 PDF → TXT로 저장 (PDF 직접 수정은 복잡하므로 텍스트 추출)"""
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = original_path.stem
    out_name = f"BRJ{brj_number}_{stem}.txt"
    out_path = output_dir / out_name
    out_path.write_text(text, encoding='utf-8')
    return out_path


def backup_original(filepath: Path, backup_dir: Path):
    """원본 파일을 백업 폴더로 복사"""
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"{ts}_{filepath.name}"
    dest = backup_dir / backup_name
    shutil.copy2(str(filepath), str(dest))
    return dest


def auto_detect_candidate(filepath: Path):
    """파일명 또는 내용에서 후보자 정보 자동 감지"""
    stem = filepath.stem

    # 파일명에서 숫자 추출 (강사번호)
    numbers = re.findall(r'\b(\d{3,5})\b', stem)
    if numbers:
        for num_str in numbers:
            num = int(num_str)
            candidate = get_candidate_by_number(num)
            if candidate:
                return candidate

    # 파일명에서 이름 추출 시도
    # e.g., "1065남아공_여성(96born)" → 이름은 DB에서 찾아야 함
    # 또는 "John_Smith_Resume.docx" → "John Smith"
    name_parts = re.sub(r'[_\-]', ' ', stem)
    name_parts = re.sub(r'\d+', '', name_parts).strip()
    if name_parts and len(name_parts) > 2:
        results = lookup_candidate(name_parts)
        if len(results) == 1:
            num = results[0][0]
            candidate = get_candidate_by_number(num)
            if candidate:
                return candidate

    return None


def cmd_process(args):
    """파일/폴더 처리 명령"""
    input_path = Path(args.input)
    output_dir = Path(args.output) if args.output else DEFAULT_OUTPUT
    brj_number = args.number

    if not input_path.exists():
        print(f"[ERROR] Path not found: {input_path}")
        sys.exit(1)

    # 처리할 파일 목록
    if input_path.is_file():
        files = [input_path]
    else:
        files = sorted(
            f for f in input_path.iterdir()
            if f.suffix.lower() in ('.docx', '.pdf')
            and not f.name.startswith('~')
            and not f.name.startswith('.')
        )

    if not files:
        print(f"[INFO] No .docx/.pdf files found in {input_path}")
        return

    print(f"\n{'=' * 60}")
    print(f"  BRIDGE Document Processor v1.0")
    print(f"  Input:  {input_path}")
    print(f"  Output: {output_dir}")
    print(f"  Files:  {len(files)}")
    print(f"{'=' * 60}\n")

    for filepath in files:
        print(f"[PROCESSING] {filepath.name}")

        # 후보자 번호 결정
        current_number = brj_number
        candidate_name = None

        if current_number:
            # 명시적 번호 → DB에서 이름 조회
            candidate = get_candidate_by_number(current_number)
            if candidate:
                candidate_name = candidate[1]  # full_name
                print(f"  → Candidate: #{current_number} {candidate_name}")
            else:
                print(f"  → Number #{current_number} (not found in DB)")
        else:
            # 자동 감지
            candidate = auto_detect_candidate(filepath)
            if candidate:
                current_number = candidate[0]  # sheet_number
                candidate_name = candidate[1]  # full_name
                print(f"  → Auto-detected: #{current_number} {candidate_name}")
            else:
                # 번호 없으면 파일명에서 숫자 추출 시도
                nums = re.findall(r'\b(\d{3,5})\b', filepath.stem)
                if nums:
                    current_number = int(nums[0])
                    print(f"  → Using filename number: #{current_number}")
                else:
                    print(f"  [SKIP] Cannot determine candidate number. Use --number <N>")
                    continue

        # 원본 백업
        backup_path = backup_original(filepath, BACKUP_DIR)
        print(f"  → Backup: {backup_path.name}")

        # 파일 처리
        try:
            if filepath.suffix.lower() == '.docx':
                doc = process_docx(filepath, current_number, candidate_name)
                out_path = save_processed_docx(doc, filepath, current_number, output_dir)
                print(f"  → Output: {out_path.name}")
            elif filepath.suffix.lower() == '.pdf':
                text = process_pdf(filepath, current_number, candidate_name)
                out_path = save_processed_pdf_as_txt(text, filepath, current_number, output_dir)
                print(f"  → Output: {out_path.name} (text extracted)")
            else:
                print(f"  [SKIP] Unsupported format: {filepath.suffix}")
                continue

            print(f"  [OK] Processed successfully")

        except Exception as e:
            print(f"  [ERROR] {e}")

    print(f"\n{'=' * 60}")
    print(f"  Done! Check: {output_dir}")
    print(f"{'=' * 60}")


def cmd_lookup(args):
    """후보자 조회 명령"""
    query = args.query
    results = lookup_candidate(query)

    if not results:
        print(f"[INFO] No candidates found for: {query}")
        return

    print(f"\n{'=' * 60}")
    print(f"  Candidate Lookup: {query}")
    print(f"{'=' * 60}")
    print(f"  {'#':>5}  {'Name':<35}  {'Nationality':<12}  Email")
    print(f"  {'─' * 5}  {'─' * 35}  {'─' * 12}  {'─' * 25}")
    for row in results:
        num = row[0] or '?'
        name = (row[1] or '')[:35]
        nat = (row[2] or '')[:12]
        email = row[3] or ''
        print(f"  {num:>5}  {name:<35}  {nat:<12}  {email}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='BRIDGE Document Processor — PII 삭제 + 강사번호 입력'
    )
    sub = parser.add_subparsers(dest='command')

    # process 명령
    p_proc = sub.add_parser('process', help='문서 처리 (PII 삭제 + 번호 입력)')
    p_proc.add_argument('input', help='입력 파일 또는 폴더 경로')
    p_proc.add_argument('--number', '-n', type=int, help='강사번호 (수동 지정)')
    p_proc.add_argument('--output', '-o', help='출력 폴더 (기본: tools/processed_docs)')

    # lookup 명령
    p_look = sub.add_parser('lookup', help='후보자 조회 (이름/이메일)')
    p_look.add_argument('query', help='검색어 (이름 또는 이메일)')

    args = parser.parse_args()

    if args.command == 'process':
        cmd_process(args)
    elif args.command == 'lookup':
        cmd_lookup(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
