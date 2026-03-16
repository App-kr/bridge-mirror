# 게임 방해 프로그램 전체 중지 스크립트
# 실행: powershell -ExecutionPolicy Bypass -File stop_game_blockers.ps1

Write-Host "=== 1. HncUpdate (한글 업데이트) 중지 ===" -ForegroundColor Cyan
Stop-Service -Name "HncUpdateService_2020" -Force -ErrorAction SilentlyContinue
Set-Service  -Name "HncUpdateService_2020" -StartupType Disabled -ErrorAction SilentlyContinue
Stop-Service -Name "HncUpdateService_ODT"  -Force -ErrorAction SilentlyContinue
Set-Service  -Name "HncUpdateService_ODT"  -StartupType Disabled -ErrorAction SilentlyContinue
Get-Process  -Name "HncUpdateTray*" -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "   HncUpdate 완료"

Write-Host "=== 2. Adobe 알림 종료 ===" -ForegroundColor Cyan
Get-Process -Name "AcrobatNotificationClient" -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "   Adobe 알림 완료"

Write-Host "=== 3. OZWebLauncher 중지 ===" -ForegroundColor Cyan
Get-Process -Name "OZWebLauncher" -ErrorAction SilentlyContinue | Stop-Process -Force
Stop-Service -Name "OZWLService" -Force -ErrorAction SilentlyContinue
Set-Service  -Name "OZWLService" -StartupType Disabled -ErrorAction SilentlyContinue
Write-Host "   OZWebLauncher 완료"

Write-Host "=== 4. 금융 보안 서비스 중지 ===" -ForegroundColor Cyan
$secServices = @(
    "CrossEXService", "CrossEXLiveChecker",
    "SafeTransactionSVC",
    "AnySign4PCLauncher",
    "MagicLine4NXSVC",
    "innorixam", "innorixas",
    "WizveraPMSvc",
    "INISAFEClientManager",
    "KOS_Service",
    "nossvc",
    "Interezen_service",
    "KicaPMSvc",
    "ToucnEn_nxFirewall",
    "SignKoreaWD",
    "SnowDaemonMaker"
)
foreach ($svc in $secServices) {
    $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
    if ($s) {
        Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
        Set-Service  -Name $svc -StartupType Disabled -ErrorAction SilentlyContinue
        Write-Host "   STOP: $svc"
    }
}

Write-Host "=== 5. 시작 폴더 정리 ===" -ForegroundColor Cyan
$startupPath = [System.Environment]::GetFolderPath('Startup')
$commonPath  = [System.Environment]::GetFolderPath('CommonStartup')

$removeItems = @("MeetAlarm.lnk", "AudioToggle.lnk")
foreach ($item in $removeItems) {
    $full = Join-Path $startupPath $item
    if (Test-Path $full) {
        Remove-Item $full -Force
        Write-Host "   제거: $item"
    }
}

$commonItems = @("G2BRUN.lnk")
foreach ($item in $commonItems) {
    $full = Join-Path $commonPath $item
    if (Test-Path $full) {
        Remove-Item $full -Force
        Write-Host "   제거(공통): $item"
    }
}

Write-Host "=== 6. Bridge 백업 스케줄 작업 — 완전 숨김 확인 ===" -ForegroundColor Cyan
# AutoBackup5min은 pythonw로 실행 (숨김창) — 유지
# ClaudeBlog_AutoBackup이 cmd 창을 띄우는지 확인
$task = Get-ScheduledTask -TaskName "ClaudeBlog_AutoBackup" -ErrorAction SilentlyContinue
if ($task) {
    $action = $task.Actions[0]
    Write-Host "   ClaudeBlog_AutoBackup 실행: $($action.Execute) $($action.Arguments)"
    # cmd /c로 실행되면 창이 뜸 -> 비활성화
    if ($action.Execute -like "*cmd*" -or $action.Arguments -like "*/c*") {
        Disable-ScheduledTask -TaskName "ClaudeBlog_AutoBackup" -ErrorAction SilentlyContinue
        Write-Host "   -> cmd 창 감지, 비활성화 완료"
    }
} else {
    Write-Host "   ClaudeBlog_AutoBackup 없음"
}

Write-Host "=== 7. 레지스트리 시작프로그램 정리 ===" -ForegroundColor Cyan
$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$removeReg = @("CrossEX", "RAONK", "RAONWIZNote", "stsess", "AnySign4PC", "MagicLine", "OZWebLauncher", "HncUpdateTray")
foreach ($r in $removeReg) {
    if (Get-ItemProperty -Path $regPath -Name $r -ErrorAction SilentlyContinue) {
        Remove-ItemProperty -Path $regPath -Name $r -Force -ErrorAction SilentlyContinue
        Write-Host "   레지스트리 제거: $r"
    }
}

Write-Host ""
Write-Host "=== 완료 ===" -ForegroundColor Green
Write-Host "현재 실행 중인 시작폴더:" $startupPath
Get-ChildItem $startupPath -ErrorAction SilentlyContinue | Select-Object Name | Format-Table -HideTableHeaders
