# Task Scheduler 자동 실행 테스트
Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue

$logFile = "C:\Users\Scarlett\AppData\Local\bridge_headset_switch.log"

# 1. 테스트 전 현재 기본 장치
$before = (Get-AudioDevice -Playback).Name
Write-Host "[BEFORE] 현재 기본 출력: $before"

# 2. 로그 초기화 (이전 기록 삭제)
if (Test-Path $logFile) { Remove-Item $logFile -Force }
Write-Host "[LOG] 로그 초기화 완료"

# 3. Task Scheduler 강제 실행
Write-Host "[TASK] ABKO_N460_AutoConnect 강제 실행..."
Start-ScheduledTask -TaskName "ABKO_N460_AutoConnect"

# 4. 실행 완료 대기 (최대 10초)
$elapsed = 0
do {
    Start-Sleep -Seconds 1
    $elapsed++
    $info = Get-ScheduledTaskInfo -TaskName "ABKO_N460_AutoConnect"
    $state = (Get-ScheduledTask -TaskName "ABKO_N460_AutoConnect").State
    Write-Host "  [$elapsed s] Task 상태: $state | 마지막 실행: $($info.LastRunTime)"
} while ($state -eq "Running" -and $elapsed -lt 10)

# 5. 결과 확인
$info = Get-ScheduledTaskInfo -TaskName "ABKO_N460_AutoConnect"
Write-Host ""
Write-Host "=== Task 실행 결과 ==="
Write-Host "마지막 실행 시각: $($info.LastRunTime)"
Write-Host "종료 코드: $($info.LastTaskResult) (0=성공)"

# 6. 로그 확인
Write-Host ""
Write-Host "=== 스크립트 로그 ==="
if (Test-Path $logFile) {
    Get-Content $logFile
} else {
    Write-Host "로그 파일 없음 (실행 안 됨)"
}

# 7. 이벤트 트리거 확인
Write-Host ""
Write-Host "=== Task Scheduler 트리거 정보 ==="
$task = Get-ScheduledTask -TaskName "ABKO_N460_AutoConnect"
$task.Triggers | Format-List
