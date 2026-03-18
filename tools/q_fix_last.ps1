$ErrorActionPreference = "SilentlyContinue"

# 남은 깨진 폴더 파악
$remaining = Get-ChildItem "Q:\" -Force -Directory | Where-Object {
    ($_.Name -replace '[^\x20-\x7E]', '').Length -ne $_.Name.Length
}
foreach ($dir in $remaining) {
    Write-Host "Still garbled: [$($dir.Name)]"
    $files = Get-ChildItem $dir.FullName -Force -ErrorAction SilentlyContinue
    Write-Host "  Count: $($files.Count)"
    $files | Select-Object -First 5 | ForEach-Object { Write-Host "  - $($_.Name) ($($_.Length) bytes)" }
}

# Filezilla 내부 확인
Write-Host "`nFilezilla contents:"
Get-ChildItem "Q:\Filezilla" -Force -Recurse -ErrorAction SilentlyContinue | Select-Object FullName, Length
