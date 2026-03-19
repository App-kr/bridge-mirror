# Read the text instruction file
$txtPath = "C:\Users\Scarlett\Desktop\Adobe Acrobat Pro DC 2020(PW123)\" + [char]0xC0D0 + " " + [char]0xD14D + [char]0xC2A4 + [char]0xD2B8 + " " + [char]0xD30C + [char]0xC77C + ".txt"
# Try direct
$files = Get-ChildItem "C:\Users\Scarlett\Desktop\Adobe Acrobat Pro DC 2020(PW123)" -Filter "*.txt"
foreach ($f in $files) {
    Write-Host "=== $($f.Name) ==="
    Get-Content $f.FullName -Encoding UTF8 -ErrorAction SilentlyContinue
    Get-Content $f.FullName -Encoding Default -ErrorAction SilentlyContinue
}

Write-Host "`n=== 2019 base folder ==="
$base = "C:\Users\Scarlett\Desktop\Adobe Acrobat Pro DC 2020(PW123)\Adobe Acrobat Pro DC 2020\Adobe Acrobat Pro DC 2019"
Get-ChildItem $base -ErrorAction SilentlyContinue | Format-Table Name, Extension, Length
