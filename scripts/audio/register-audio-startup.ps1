# register-audio-startup.ps1
# 로그인 시 스피커 강제 설정 작업을 Task Scheduler에 등록

$taskName = "BridgeAudioStartup"
$scriptPath = "Q:\Claudework\bridge base\scripts\audio\audio-startup.ps1"

# 기존 작업 제거
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "기존 작업 제거됨"
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

# 로그인 시 + 10초 딜레이 (드라이버 로드 대기)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger.Delay = "PT10S"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit "PT1M" `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries

$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "로그인 시 스피커를 기본 오디오 장치로 강제 설정 (헤드셋 자동 선택 방지)" `
    -Force | Out-Null

Write-Host "✅ '$taskName' 작업 등록 완료"
Write-Host "   실행 조건: 로그인 후 10초 대기 → 스피커 강제 설정"
