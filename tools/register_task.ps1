# AudioAutoSwitcher 작업 스케줄러 등록
$taskName = 'AudioAutoSwitcher'
$vbsPath = 'Q:\Claudework\bridge base\tools\audio_switcher_run.vbs'

$action = New-ScheduledTaskAction `
    -Execute 'wscript.exe' `
    -Argument "`"$vbsPath`""

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit 0 `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 2) `
    -StartWhenAvailable

# 기존 삭제 후 재등록
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force

Write-Host "등록 완료: $taskName"
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, State | Format-Table
