# _BACKUP 내부 구조 확인
$snapDir = "Q:\Claudework\_BACKUP"
$snaps = Get-ChildItem $snapDir -Directory | Sort-Object Name -Descending | Select-Object -First 1

Write-Host "=== 최신 스냅샷 최상위 폴더 ==="
Get-ChildItem $snaps.FullName | Select-Object Name, Mode | Format-Table -AutoSize

Write-Host ""
Write-Host "=== _BACKUP 경로 참조 스크립트 검색 ==="
Get-ChildItem "Q:\Claudework" -Recurse -Include "*.ps1","*.py","*.bat" -ErrorAction SilentlyContinue |
    Select-String -Pattern "_BACKUP" -ErrorAction SilentlyContinue |
    Select-Object Filename, LineNumber, Line | Format-Table -AutoSize -Wrap
