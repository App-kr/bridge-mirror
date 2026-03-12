# Windows Terminal 세션 및 오전 10시 이후 작업 복구
$wtState = "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState"
$since = (Get-Date).Date.AddHours(10)

Write-Host "=== Windows Terminal 상태 파일 ===" -ForegroundColor Cyan
if (Test-Path $wtState) {
    Get-ChildItem $wtState | Where-Object { $_.LastWriteTime -gt $since } |
        Select-Object Name, LastWriteTime | Format-Table -AutoSize

    $layoutFile = Join-Path $wtState "window-layout.json"
    if (Test-Path $layoutFile) {
        Write-Host "`n=== window-layout.json ===" -ForegroundColor Yellow
        Get-Content $layoutFile -Raw | ConvertFrom-Json | ConvertTo-Json -Depth 10
    }
} else {
    Write-Host "Windows Terminal 상태 폴더 없음"
}

Write-Host "`n=== PowerShell 히스토리 (오전 10시 이후) ===" -ForegroundColor Cyan
$histFile = "$env:APPDATA\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt"
if (Test-Path $histFile) {
    $modTime = (Get-Item $histFile).LastWriteTime
    Write-Host "히스토리 파일 최종 수정: $modTime"
    # 최근 50개 명령
    Get-Content $histFile | Select-Object -Last 50
}

Write-Host "`n=== 오전 10시 이후 수정된 파일 (Q드라이브) ===" -ForegroundColor Cyan
Get-ChildItem "Q:\Claudework" -Recurse -ErrorAction SilentlyContinue |
    Where-Object { -not $_.PSIsContainer -and $_.LastWriteTime -gt $since } |
    Select-Object FullName, LastWriteTime |
    Sort-Object LastWriteTime |
    Format-Table -AutoSize
