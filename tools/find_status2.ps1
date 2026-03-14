# Windows Terminal 및 Claude Code statusline 확인
Write-Host "=== Windows Terminal 설정 파일 검색 ==="
@(
    "$env:LOCALAPPDATA\Microsoft\Windows Terminal\settings.json",
    "$env:APPDATA\Microsoft\Windows Terminal\settings.json"
) | ForEach-Object {
    if (Test-Path $_) {
        Write-Host "FOUND: $_"
        Get-Content $_ -Raw | ConvertFrom-Json | Select-Object -Property startupActions, theme | Format-List
    }
}

# Windows Terminal 패키지 (다른 버전)
Get-ChildItem "$env:LOCALAPPDATA\Packages" -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like '*Terminal*' } | Select-Object Name, FullName

Write-Host "`n=== Claude Code settings.json ==="
$ccSettings = "$env:APPDATA\Claude\settings.json"
if (Test-Path $ccSettings) {
    Write-Host "FOUND: $ccSettings"
    Get-Content $ccSettings -Raw
}
# 다른 경로
@("$env:USERPROFILE\.claude\settings.json") | ForEach-Object {
    if (Test-Path $_) {
        Write-Host "FOUND: $_"
        Get-Content $_ -Raw
    }
}

Write-Host "`n=== HKCU Run 항목 상세 (값 없는 항목 포함) ==="
$runKey = Get-Item "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
$runKey.GetValueNames() | ForEach-Object {
    $val = $runKey.GetValue($_)
    Write-Host "$_ = $val"
}

Write-Host "`n=== 최근 2주 winget 설치 내역 ==="
Get-WinEvent -LogName "Microsoft-Windows-AppXDeployment-Server/Operational" -MaxEvents 50 -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match 'install' } |
    Select-Object TimeCreated, Message -First 10 | Format-List

Write-Host "`n=== Q드라이브 최근 1주일 수정 파일 (py/bat/ps1) ==="
Get-ChildItem "Q:\" -Recurse -Include @("*.py","*.bat","*.ps1","*.exe") -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-7) } |
    Where-Object { $_.FullName -notmatch '_BACKUP|backups|__pycache__' } |
    Select-Object FullName, LastWriteTime | Sort-Object LastWriteTime -Descending | Select-Object -First 20
