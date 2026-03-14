# audio_switcher_run.vbs 존재 및 실제 경로 검증
Write-Host "=== audio_switcher_run.vbs 경로 검증 ==="
$vbs = "Q:\Claudework\bridge base\tools\audio_switcher_run.vbs"
if (Test-Path $vbs) {
    Write-Host "EXISTS: $vbs"
    Get-Content $vbs
} else {
    Write-Host "NOT EXISTS: $vbs"
}

Write-Host "`n=== AudioAutoSwitcher 태스크 실제 XML 추출 ==="
Export-ScheduledTask -TaskName 'AudioAutoSwitcher' -ErrorAction SilentlyContinue

Write-Host "`n=== Task Scheduler 로그 (AudioAutoSwitcher 오류) ==="
Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational' -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match 'AudioAutoSwitcher' -or $_.Message -match 'audio_switch' } |
    Select-Object TimeCreated, Id, Message -First 5 | Format-List

Write-Host "`n=== 모든 Task Scheduler 작업 실패 로그 (최근 24시간) ==="
Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational' -ErrorAction SilentlyContinue |
    Where-Object { $_.LevelDisplayName -eq 'Error' -and $_.TimeCreated -gt (Get-Date).AddDays(-1) } |
    Select-Object TimeCreated, Id, Message -First 10 | Format-List
