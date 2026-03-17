# -*- coding: utf-8 -*-
import zipfile, re, sys
sys.stdout.reconfigure(encoding="utf-8")

xlsx = r"Q:\Claudework\bridge base\웹빌드_자료\테스트용_지원자접수.xlsx"
docx = r"Q:\Claudework\bridge base\웹빌드_자료\테스트용_정리.docx"

print("="*60)
print("XLSX - shared strings list")
print("="*60)

with zipfile.ZipFile(xlsx, "r") as z:
    names = z.namelist()
    
    # Shared strings - get full <si> elements to preserve order
    strings = []
    if "xl/sharedStrings.xml" in names:
        with z.open("xl/sharedStrings.xml") as f:
            ss = f.read().decode("utf-8")
        # Each <si> block is one string entry
        si_blocks = re.findall(r"<si>(.*?)</si>", ss, re.DOTALL)
        for si in si_blocks:
            texts = re.findall(r"<t(?:\s[^>]*)?>([^<]*)</t>", si)
            strings.append("".join(texts))
    
    print(f"Total shared strings: {len(strings)}")
    print("First 50 strings:")
    for i, s in enumerate(strings[:50]):
        print(f"  [{i}] {s}")

print()
print("="*60)
print("XLSX - Sheet1 with resolved strings")
print("="*60)

with zipfile.ZipFile(xlsx, "r") as z:
    with z.open("xl/worksheets/sheet1.xml") as f:
        content = f.read().decode("utf-8")
    
    rows = re.findall(r"<row[^>]*>(.*?)</row>", content, re.DOTALL)
    for row in rows[:30]:
        cells = re.findall(r"<c r=\"([^\"]+)\"[^>]*(?:t=\"([^\"]*)\")?[^>]*>.*?<v>([^<]*)</v>", row)
        if not cells:
            continue
        row_data = []
        for ref, ctype, val in cells:
            if ctype == "s":
                try:
                    display = strings[int(val)]
                except:
                    display = f"[ss:{val}]"
            else:
                display = val
            row_data.append(f"{ref}={display}")
        if row_data:
            print(" | ".join(row_data))

print()
print("="*60)
print("XLSX - Sheet2 with resolved strings")
print("="*60)

with zipfile.ZipFile(xlsx, "r") as z:
    with z.open("xl/worksheets/sheet2.xml") as f:
        content = f.read().decode("utf-8")
    
    rows = re.findall(r"<row[^>]*>(.*?)</row>", content, re.DOTALL)
    for row in rows[:200]:
        cells = re.findall(r"<c r=\"([^\"]+)\"[^>]*(?:t=\"([^\"]*)\")?[^>]*>.*?<v>([^<]*)</v>", row)
        if not cells:
            continue
        row_data = []
        for ref, ctype, val in cells:
            if ctype == "s":
                try:
                    display = strings[int(val)]
                except:
                    display = f"[ss:{val}]"
            else:
                display = val
            row_data.append(f"{ref}={display}")
        if row_data:
            print(" | ".join(row_data))

print()
print("="*60)
print("XLSX - Sheet3 with resolved strings")
print("="*60)

with zipfile.ZipFile(xlsx, "r") as z:
    with z.open("xl/worksheets/sheet3.xml") as f:
        content = f.read().decode("utf-8")
    
    rows = re.findall(r"<row[^>]*>(.*?)</row>", content, re.DOTALL)
    for row in rows[:10]:
        cells = re.findall(r"<c r=\"([^\"]+)\"[^>]*(?:t=\"([^\"]*)\")?[^>]*>.*?<v>([^<]*)</v>", row)
        if not cells:
            continue
        row_data = []
        for ref, ctype, val in cells:
            if ctype == "s":
                try:
                    display = strings[int(val)]
                except:
                    display = f"[ss:{val}]"
            else:
                display = val
            row_data.append(f"{ref}={display}")
        if row_data:
            print(" | ".join(row_data))

print()
print("="*60)
print("XLSX - Sheet4 with resolved strings")
print("="*60)

with zipfile.ZipFile(xlsx, "r") as z:
    with z.open("xl/worksheets/sheet4.xml") as f:
        content = f.read().decode("utf-8")
    
    rows = re.findall(r"<row[^>]*>(.*?)</row>", content, re.DOTALL)
    for row in rows[:10]:
        cells = re.findall(r"<c r=\"([^\"]+)\"[^>]*(?:t=\"([^\"]*)\")?[^>]*>.*?<v>([^<]*)</v>", row)
        if not cells:
            continue
        row_data = []
        for ref, ctype, val in cells:
            if ctype == "s":
                try:
                    display = strings[int(val)]
                except:
                    display = f"[ss:{val}]"
            else:
                display = val
            row_data.append(f"{ref}={display}")
        if row_data:
            print(" | ".join(row_data))
