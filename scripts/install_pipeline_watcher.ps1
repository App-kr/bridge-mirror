# Pipeline Failure Watcher — Windows 작업 스케줄러 자동 등록
# 실행: powershell -ExecutionPolicy Bypass -File .\scripts\install_pipeline_watcher.ps1

$TaskName  = "BRIDGE_PipelineWatcher"
$BatPath   = "Q:\Claudework\bridge base\scripts\start_pipeline_watcher.bat"
$LogPath   = "Q:\Claudework\bridge base\logs\watcher.log"

Write-Host "=== Pipeline Failure Watcher 자동시작 등록 ===" -ForegroundColor Cyan

# 기존 작업 제거
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "[OK] 기존 작업 제거됨" -ForegroundColor Yellow
}

# 트리거: 로그온 시 (현재 사용자)
$Trigger  = New-ScheduledTaskTrigger -AtLogon -User $env:USERNAME

# 동작: bat 파일 실행 (최소화 창)
$Action   = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatPath`" >> `"$LogPath`" 2>&1" `
    -WorkingDirectory "Q:\Claudework\bridge base"

# 설정: 항상 실행, 배터리 포함
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName  $TaskName `
    -Trigger   $Trigger `
    -Action    $Action `
    -Settings  $Settings `
    -RunLevel  Highest `
    -Description "BRIDGE 파이프라인 DLQ 실패 감시 데몬 (60초 주기)" `
    -Force | Out-Null

Write-Host "[OK] 작업 스케줄러 등록 완료: $TaskName" -ForegroundColor Green
Write-Host "  트리거 : 로그온 시 자동 시작" -ForegroundColor White
Write-Host "  로그    : $LogPath" -ForegroundColor White
Write-Host ""
Write-Host "지금 바로 시작하려면:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
Write-Host ""

# 즉시 시작 여부 확인
$yn = Read-Host "지금 바로 시작하시겠습니까? (Y/N)"
if ($yn -match "^[Yy]") {
    Start-ScheduledTask -TaskName $TaskName
    Start-Sleep -Seconds 2
    $State = (Get-ScheduledTask -TaskName $TaskName).State
    Write-Host "[OK] 시작됨, 상태: $State" -ForegroundColor Green
}
