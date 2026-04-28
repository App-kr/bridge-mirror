$ErrorActionPreference = 'Stop'

$pythonw = "Q:\Phtyon 3\pythonw.exe"
$script = "Q:\Claudework\bridge base\tools\game_mode_guardian.py"

if (-not (Test-Path $pythonw)) { Write-Host "FATAL: $pythonw"; exit 1 }
if (-not (Test-Path $script))   { Write-Host "FATAL: $script";   exit 1 }

$action = New-ScheduledTaskAction -Execute $pythonw -Argument "-X utf8 `"$script`""
$trigger = New-ScheduledTaskTrigger -AtLogon
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -Hidden `
    -ExecutionTimeLimit (New-TimeSpan -Days 365) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew

Unregister-ScheduledTask -TaskName "BRIDGE_GameModeGuardian" -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName "BRIDGE_GameModeGuardian" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Auto-suspend non-essential BRIDGE tasks during game sessions; resume after 5min grace" `
    -RunLevel Limited | Out-Null

Write-Host "OK: BRIDGE_GameModeGuardian registered"

Start-ScheduledTask -TaskName "BRIDGE_GameModeGuardian"
Start-Sleep -Seconds 2

$proc = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*game_mode_guardian*' } | Select-Object -First 1
if ($proc) {
    Write-Host ("OK: PID={0} running" -f $proc.ProcessId)
} else {
    Write-Host "WARN: process not detected (check Task History)"
}
