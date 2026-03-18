"""Register BridgeAudioStartup in Task Scheduler."""
import subprocess, sys

TASK_NAME = "BridgeAudioStartup"
SCRIPT_PATH = r"Q:\Claudework\bridge base\scripts\audio\audio-startup.ps1"

PS = r"""
$taskName = "BridgeAudioStartup"
$scriptPath = "Q:\Claudework\bridge base\scripts\audio\audio-startup.ps1"

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Removed old task"
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument ("-WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File `"" + $scriptPath + "`"")

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
    -Description "Force speaker as default audio on login" `
    -Force | Out-Null

$t = Get-ScheduledTask -TaskName $taskName
Write-Host ("OK: " + $t.TaskName + " | State=" + $t.State)
"""

result = subprocess.run(
    ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", PS],
    capture_output=True, text=True, encoding="utf-8"
)
print(result.stdout)
if result.returncode != 0:
    print("STDERR:", result.stderr)
    sys.exit(1)
