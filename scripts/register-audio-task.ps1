# register-audio-task.ps1
# AudioAutoSwitch 작업 스케줄러 등록

$scriptPath = 'Q:\Claudework\bridge base\scripts\audio-switch.ps1'

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

# Remove existing task if present
$existing = Get-ScheduledTask -TaskName 'AudioAutoSwitch' -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName 'AudioAutoSwitch' -Confirm:$false
    Write-Host "Existing task removed." -ForegroundColor Yellow
}

Register-ScheduledTask -TaskName 'AudioAutoSwitch' -Action $action -Trigger $trigger -Settings $settings -Description 'Captain 780LITE headset auto-switch' -RunLevel Highest

Write-Host "AudioAutoSwitch task registered successfully!" -ForegroundColor Green
Write-Host "The script will run automatically at next login." -ForegroundColor Cyan
