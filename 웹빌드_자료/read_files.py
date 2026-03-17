# -*- coding: utf-8 -*-
import zipfile, re, sys
sys.stdout.reconfigure(encoding='utf-8')

xlsx = r'Q:\Claudework\bridge base\웹빌드_자료\테스트용_지원자접수.xlsx'
docx = r'Q:\Claudework\bridge base\웹빌드_자료\테스트용_정리.docx'

# ── XLSX ──
print("="*60)
print("XLSX 전체 내용")
print("="*60)

with zipfile.ZipFile(xlsx, 'r') as z:
    names = z.namelist()
    strings = []
    if 'xl/sharedStrings.xml' in names:
        with z.open('xl/sharedStrings.xml') as f:
            ss = f.read().decode('utf-8')
        strings = re.findall(r'<t(?:\s[^>]*)?>([^<]*)</t>', ss)

    with z.open('xl/workbook.xml') as f:
        wb = f.read().decode('utf-8')
    sheet_names = re.findall(r'<sheet name="([^"]+)"', wb)
    print(f"시트 목록: {sheet_names}\n")

    sheet_files = sorted([n for n in names if re.match(r'xl/worksheets/sheet\d+\.xml', n)])

    for i, sf in enumerate(sheet_files):
        sname = sheet_names[i] if i < len(sheet_names) else f'Sheet{i+1}'
        print(f'\n{"="*50}')
        print(f'시트: {sname}')
        print('='*50)
        with z.open(sf) as f:
            content = f.read().decode('utf-8')
        rows = re.findall(r'<row[^>]*>(.*?)</row>', content, re.DOTALL)
        for row in rows[:100]:
            cells = re.findall(r'<c r="([^"]+)"[^>]*(?:t="([^"]*)")?[^>]*>.*?<v>([^<]*)</v>', row)
            if not cells:
                continue
            row_data = []
            for ref, ctype, val in cells:
                if ctype == 's':
                    try: display = strings[int(val)]
                    except: display = val
                else:
                    display = val
                row_data.append(f'{ref}={display}')
            if row_data:
                print(' | '.join(row_data))

# ── DOCX ──
print("\n" + "="*60)
print("DOCX 전체 내용")
print("="*60)
with zipfile.ZipFile(docx, 'r') as z:
    with z.open('word/document.xml') as f:
        content = f.read().decode('utf-8')
paras = re.findall(r'<w:p[ >].*?</w:p>', content, re.DOTALL)
for p in paras:
    texts = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p)
    line = ''.join(texts).strip()
    if line:
        print(line)
