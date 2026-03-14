# Q드라이브에서 상태 모니터링 관련 파일 검색
Write-Host "=== Q드라이브 내 상태그래프/모니터링 관련 파일 ==="
Get-ChildItem "Q:\" -Recurse -ErrorAction SilentlyContinue -Include @(
    "*.py", "*.bat", "*.cmd", "*.ps1", "*.ahk", "*.exe", "*.sh"
) | Where-Object {
    $_.Name -match 'status|monitor|graph|overlay|dashboard|widget|tray|tracker|watch' -or
    $_.FullName -match 'status|monitor|graph|overlay|dashboard|widget|tracker'
} | Select-Object FullName, LastWriteTime | Sort-Object LastWriteTime -Descending | Select-Object -First 30

Write-Host "`n=== Claudeother 폴더 내용 ==="
Get-ChildItem "Q:\Claudeother" -Recurse -ErrorAction SilentlyContinue | Select-Object FullName, LastWriteTime | Sort-Object LastWriteTime -Descending | Select-Object -First 20

Write-Host "`n=== bridge-overnight 폴더 ==="
Get-ChildItem "Q:\bridge-overnight" -ErrorAction SilentlyContinue | Select-Object Name, LastWriteTime

Write-Host "`n=== Codex testing 폴더 ==="
Get-ChildItem "Q:\Codex testing" -ErrorAction SilentlyContinue | Select-Object Name, LastWriteTime
