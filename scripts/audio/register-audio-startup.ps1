# register-audio-startup.ps1
# USB Headset auto-detection task registration

$taskName = "BridgeAudioStartup"
$scriptPath = "Q:\Claudework\bridge base\scripts\audio\audio-startup.ps1"

# Remove existing task
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Existing task removed"
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

# At login + 10 second delay (driver init)
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
    -Description "Auto-switch audio to speaker on login. USB headset auto-detection enabled." `
    -Force | Out-Null

Write-Host "OK: '$taskName' task registered"
Write-Host "    Trigger: Login + 10s delay"
Write-Host "    Actions: Speaker default + USB headset monitor"
