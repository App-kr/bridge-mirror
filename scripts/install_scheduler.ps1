$taskName = "BRIDGE_Craig_Scheduler"
$projectDir = "K:\BridgeCraig"
$pythonPath = (Get-Command python).Source

Write-Host ""
Write-Host "  BRIDGE Auto Scheduler Setup" -ForegroundColor Cyan
Write-Host "  ============================" -ForegroundColor Cyan
Write-Host ""

# === 1) Task Scheduler: every 2 hours ===
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "  Removed existing task" -ForegroundColor Yellow
}

$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "scheduler.py --once --limit 10" -WorkingDirectory $projectDir

$trigger = New-ScheduledTaskTrigger -Daily -At "01:00"
$trigger.Repetition = (New-ScheduledTaskTrigger -Once -At "01:00" -RepetitionInterval (New-TimeSpan -Hours 2) -RepetitionDuration (New-TimeSpan -Hours 23)).Repetition

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -RestartCount 1 -RestartInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "BRIDGE Craigslist multi-account auto poster (every 2 hours)" | Out-Null

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    Write-Host "  [OK] Task Scheduler registered (every 2hr)" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Task Scheduler registration failed" -ForegroundColor Red
}

# === 2) Startup shortcut: run on logon after reboot ===
$startupDir = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir "BRIDGE_Craig.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonPath
$shortcut.Arguments = "scheduler.py --once --limit 10"
$shortcut.WorkingDirectory = $projectDir
$shortcut.WindowStyle = 7  # minimized
$shortcut.Description = "BRIDGE Craig RPA on startup"
$shortcut.Save()

if (Test-Path $shortcutPath) {
    Write-Host "  [OK] Startup shortcut created (runs on logon)" -ForegroundColor Green
    Write-Host "       $shortcutPath" -ForegroundColor DarkGray
} else {
    Write-Host "  [FAIL] Startup shortcut creation failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "  Summary:" -ForegroundColor Cyan
Write-Host "  - Every 2hr : Task Scheduler (01,03,05...23)" -ForegroundColor Gray
Write-Host "  - On reboot  : Startup shortcut (runs immediately)" -ForegroundColor Gray
Write-Host "  - Cooldown   : 4hr per account" -ForegroundColor Gray
Write-Host "  - account1   : 01,07,13,19" -ForegroundColor Gray
Write-Host "  - account2   : 03,09,15,21" -ForegroundColor Gray
Write-Host "  - account3   : 05,11,17,23" -ForegroundColor Gray
Write-Host ""
