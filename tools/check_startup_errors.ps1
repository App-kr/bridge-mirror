# 오류 박스 유발 가능한 시작 스크립트 점검

Write-Host "=== AudioAutoSwitcher 태스크 상세 ==="
$t = Get-ScheduledTask -TaskName 'AudioAutoSwitcher' -ErrorAction SilentlyContinue
if ($t) {
    $t.Actions | Format-List
    $t.Triggers | Format-List
}

Write-Host "=== AudioSwitcher 태스크 상세 ==="
$t2 = Get-ScheduledTask -TaskName 'AudioSwitcher' -ErrorAction SilentlyContinue
if ($t2) {
    $t2.Actions | Format-List
    $t2.Triggers | Format-List
}

Write-Host "=== BridgeCrRL 태스크 상세 ==="
Get-ScheduledTask | Where-Object { $_.TaskName -like 'BridgeCrRL*' } | ForEach-Object {
    Write-Host "Task: $($_.TaskName) | State: $($_.State)"
    $_.Actions | Format-List
}

Write-Host "=== audio-toggle.ahk 내용 ==="
if (Test-Path "Q:\Headset\audio-toggle.ahk") {
    Get-Content "Q:\Headset\audio-toggle.ahk" | Select-Object -First 30
}

Write-Host "`n=== 최근 Application 이벤트 오류 (오늘) ==="
Get-WinEvent -LogName Application -MaxEvents 200 -ErrorAction SilentlyContinue |
    Where-Object { $_.LevelDisplayName -eq 'Error' -and $_.TimeCreated -gt (Get-Date).AddDays(-1) } |
    Select-Object TimeCreated, ProviderName, Message -First 10 | Format-List

Write-Host "`n=== Windows 이벤트 로그 — 시작 시 오류 ==="
Get-WinEvent -LogName System -MaxEvents 100 -ErrorAction SilentlyContinue |
    Where-Object { $_.LevelDisplayName -eq 'Error' -and $_.TimeCreated -gt (Get-Date).AddHours(-2) } |
    Select-Object TimeCreated, ProviderName, Message -First 10 | Format-List
