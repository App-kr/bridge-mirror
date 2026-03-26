# 시작프로그램 및 스케줄러 확인
Write-Host "=== 작업 스케줄러 (PowerShell/Python 포함) ===" -ForegroundColor Cyan

$tasks = Get-ScheduledTask | ForEach-Object {
    $t = $_
    $actions = $t.Actions | ForEach-Object { $_.Execute + " " + $_.Arguments }
    [PSCustomObject]@{
        Name    = $t.TaskName
        Path    = $t.TaskPath
        Command = $actions -join "; "
        State   = $t.State
    }
} | Where-Object { $_.Command -match "powershell|python|\.py|bridge|claude" }

if ($tasks) {
    $tasks | Format-Table -AutoSize -Wrap
} else {
    Write-Host "  (없음)"
}

Write-Host "`n=== 시작 폴더 (Startup) ===" -ForegroundColor Cyan
$startupUser = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$startupAll  = "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"

Write-Host "User Startup: $startupUser"
Get-ChildItem $startupUser -ErrorAction SilentlyContinue | Select-Object Name, FullName | Format-Table -AutoSize

Write-Host "AllUsers Startup: $startupAll"
Get-ChildItem $startupAll -ErrorAction SilentlyContinue | Select-Object Name, FullName | Format-Table -AutoSize

Write-Host "`n=== 레지스트리 Run 키 ===" -ForegroundColor Cyan
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue | Format-List
Get-ItemProperty "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue | Format-List
Get-ItemProperty "HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue | Format-List

Write-Host "`n=== 현재 실행 중인 PowerShell 프로세스 ===" -ForegroundColor Cyan
Get-Process | Where-Object { $_.Name -match "powershell|pwsh|python" } | Select-Object Id, Name, Path, StartTime | Format-Table -AutoSize
