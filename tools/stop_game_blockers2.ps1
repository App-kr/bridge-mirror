# 2차 정리 스크립트

# 1. ClaudeBlog_AutoBackup 스케줄 작업 -> wscript 숨김 실행으로 변경
$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"Q:\Claudework\ClaudeBlog\auto_backup_silent.vbs`""
Set-ScheduledTask -TaskName "ClaudeBlog_AutoBackup" -Action $action -ErrorAction SilentlyContinue
Write-Host "ClaudeBlog_AutoBackup -> wscript 숨김 전환 완료"

# 2. AhnLab Safe Transaction 트레이 제거
Remove-ItemProperty -Path "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "AhnLab Safe Transaction Application" -Force -ErrorAction SilentlyContinue
Write-Host "AhnLab Safe Transaction 트레이 시작 제거 완료"

# 3. Adobe CCX 제거
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "CCXProcess" -Force -ErrorAction SilentlyContinue
Write-Host "Adobe CCX 시작 제거 완료"

# 4. stsess (AhnLab 트레이 프로세스) 강제 종료
Get-Process -Name "stsess" -ErrorAction SilentlyContinue | ForEach-Object {
    taskkill /PID $_.Id /F 2>$null
}
Get-Process -Name "CCXProcess" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "AhnLab 트레이 프로세스 종료 시도 완료"

# 5. 현재 HKCU Run 목록 (남은 항목 확인)
Write-Host ""
Write-Host "=== 최종 시작프로그램 목록 (HKCU) ==="
$reg = Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$reg.PSObject.Properties | Where-Object { $_.Name -notmatch "^PS" } | Select-Object Name, Value | Format-Table -AutoSize

Write-Host "=== 최종 시작프로그램 목록 (HKLM) ==="
$reg2 = Get-ItemProperty "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run"
$reg2.PSObject.Properties | Where-Object { $_.Name -notmatch "^PS" } | Select-Object Name, Value | Format-Table -AutoSize

Write-Host ""
Write-Host "=== 비활성화된 서비스 확인 ==="
Get-Service | Where-Object { $_.StartType -eq "Disabled" -and $_.DisplayName -match "Hnc|Ahnlab|Magic|Inno|Raon|nProtect|Cross|Sign|Wizvera|Touchen|Interezen|OZWeb|KOS|KICA|Snow" } |
    Select-Object Name, DisplayName, Status | Format-Table -AutoSize
