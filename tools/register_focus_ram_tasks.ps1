# Register focus_guard (always-on) + ram_watchdog (30-min) in Task Scheduler
# All run via pythonw.exe (no console window) + Hidden setting
$ErrorActionPreference = 'Stop'

$pythonw = "Q:\Phtyon 3\pythonw.exe"
if (-not (Test-Path $pythonw)) {
    Write-Host "FATAL: $pythonw not found"
    exit 1
}

# ── 1) BRIDGE_FocusGuard - OnLogon, runs forever ──
$focusScript = "Q:\Claudework\bridge base\tools\focus_guard.py"
if (-not (Test-Path $focusScript)) { Write-Host "FATAL: focus_guard.py missing"; exit 1 }

$action1 = New-ScheduledTaskAction -Execute $pythonw -Argument "-X utf8 `"$focusScript`""
$trigger1 = New-ScheduledTaskTrigger -AtLogon
$settings1 = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -Hidden `
    -ExecutionTimeLimit (New-TimeSpan -Days 365) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Remove if exists
Unregister-ScheduledTask -TaskName "BRIDGE_FocusGuard" -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName "BRIDGE_FocusGuard" `
    -Action $action1 `
    -Trigger $trigger1 `
    -Settings $settings1 `
    -Description "Hide cmd/powershell popups during games (focus-steal protection)" `
    -RunLevel Limited | Out-Null

Write-Host "OK: BRIDGE_FocusGuard registered (OnLogon, hidden)"

# ── 2) BRIDGE_RAMWatchdog - every 30 min ──
$watchScript = "Q:\Claudework\bridge base\tools\ram_watchdog.py"
if (-not (Test-Path $watchScript)) { Write-Host "FATAL: ram_watchdog.py missing"; exit 1 }

$action2 = New-ScheduledTaskAction -Execute $pythonw -Argument "-X utf8 `"$watchScript`""
$trigger2 = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(2)) `
    -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -RepetitionDuration ([System.TimeSpan]::MaxValue)

$settings2 = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -Hidden `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

Unregister-ScheduledTask -TaskName "BRIDGE_RAMWatchdog" -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName "BRIDGE_RAMWatchdog" `
    -Action $action2 `
    -Trigger $trigger2 `
    -Settings $settings2 `
    -Description "Auto-kill lingering one-shot tasks (RPA/blog/mail) after 30min idle" `
    -RunLevel Limited | Out-Null

Write-Host "OK: BRIDGE_RAMWatchdog registered (every 30min, hidden)"

# ── 3) Start FocusGuard immediately (so user feels effect now) ──
Start-ScheduledTask -TaskName "BRIDGE_FocusGuard"
Start-Sleep -Seconds 2

$running = Get-Process pythonw -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like '*focus_guard.py*'
}
if ($running) {
    Write-Host "OK: FocusGuard PID=$($running.Id) running"
} else {
    Write-Host "WARN: FocusGuard process not detected (check task history)"
}

Write-Host "`n=== Verification ==="
Get-ScheduledTask -TaskName 'BRIDGE_FocusGuard','BRIDGE_RAMWatchdog' | ForEach-Object {
    $info = $_ | Get-ScheduledTaskInfo
    Write-Host ("  {0}: state={1} lastRun={2} nextRun={3}" -f $_.TaskName, $_.State, $info.LastRunTime, $info.NextRunTime)
}
