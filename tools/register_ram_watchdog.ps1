# RAMWatchdog only - simpler trigger
$ErrorActionPreference = 'Stop'

$pythonw = "Q:\Phtyon 3\pythonw.exe"
$watchScript = "Q:\Claudework\bridge base\tools\ram_watchdog.py"

$action = New-ScheduledTaskAction -Execute $pythonw -Argument "-X utf8 `"$watchScript`""

# Trigger: at logon, repeat every 30 min for 365 days
$trigger = New-ScheduledTaskTrigger -AtLogon
$trigger.Repetition = $(New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -RepetitionDuration (New-TimeSpan -Days 365)).Repetition

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -Hidden `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

Unregister-ScheduledTask -TaskName "BRIDGE_RAMWatchdog" -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName "BRIDGE_RAMWatchdog" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Auto-kill lingering one-shot tasks (RPA/blog/mail) after 30min idle" `
    -RunLevel Limited | Out-Null

Write-Host "OK: BRIDGE_RAMWatchdog registered"
Get-ScheduledTaskInfo -TaskName 'BRIDGE_RAMWatchdog' | Format-List State, LastRunTime, NextRunTime
