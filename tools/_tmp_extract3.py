# -*- coding: utf-8 -*-
import zipfile, re, sys
sys.stdout.reconfigure(encoding="utf-8")

xlsx = r"Q:\Claudework\bridge base\웹빌드_자료\테스트용_지원자접수.xlsx"
docx = r"Q:\Claudework\bridge base\웹빌드_자료\테스트용_정리.docx"

with zipfile.ZipFile(xlsx, "r") as z:
    names = z.namelist()
    
    # Build shared strings
    strings = []
    if "xl/sharedStrings.xml" in names:
        with z.open("xl/sharedStrings.xml") as f:
            ss = f.read().decode("utf-8")
        si_blocks = re.findall(r"<si>(.*?)</si>", ss, re.DOTALL)
        for si in si_blocks:
            # Remove xml:space=preserve and get text content
            texts = re.findall(r"<t[^>]*>([^<]*)</t>", si)
            strings.append("".join(texts))
    
    print(f"Shared strings count: {len(strings)}")
    print()
    
    def resolve_sheet(sheet_xml, label, max_rows=200):
        print("="*60)
        print(f"Sheet: {label}")
        print("="*60)
        rows = re.findall(r"<row[^>]*r=\"(\d+)\"[^>]*>(.*?)</row>", sheet_xml, re.DOTALL)
        for rnum, rowdata in rows[:max_rows]:
            # Find all cells: <c r="A1" t="s"><v>123</v> or <c r="B2"><v>3.14</v>
            cells = re.findall(r"<c r=\"([A-Z]+)(\d+)\"[^>]*(?:t=\"([^\"]*)\")[^>]*/?>.*?<v>([^<]*)</v>", rowdata, re.DOTALL)
            cells_no_t = re.findall(r"<c r=\"([A-Z]+)(\d+)\"(?![^>]*t=)[^>]*/?>.*?<v>([^<]*)</v>", rowdata, re.DOTALL)
            
            row_cells = {}
            for col, row, ctype, val in cells:
                if ctype == "s":
                    try:
                        display = strings[int(val)]
                    except:
                        display = f"[?{val}]"
                elif ctype == "inlineStr":
                    display = val
                else:
                    display = val
                row_cells[col] = display
            for col, row, val in cells_no_t:
                row_cells[col] = val
            
            if row_cells:
                parts = [f"{col}={row_cells[col]}" for col in sorted(row_cells.keys(), key=lambda c: (len(c), c))]
                print(" | ".join(parts))
    
    for sfile in sorted([n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml", n)]):
        with z.open(sfile) as f:
            content = f.read().decode("utf-8")
        resolve_sheet(content, sfile)

