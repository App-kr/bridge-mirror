# Fix: Set Hidden=True for all scheduler tasks that open visible windows
# Run: powershell -ExecutionPolicy Bypass -File fix_startup_hidden.ps1

$targetTasks = @(
    'ABKO_N460_AutoConnect',
    'ABKO_N460_StartupMonitor',
    'AudioAutoSwitcher',
    'BridgeAudioStartup',
    'BridgeCraigslistRPA',
    'BridgeInterviewReminder',
    'BridgeRenderMonitor',
    'BridgeSpeakerDefault',
    'BridgeWorkTracker',
    'ClaudeBlog_AutoBackup',
    'HeadsetManager',
    'QDriveBackupDaemon',
    'SpeakerDefaultOnLogon',
    'TeastPost30Day',
    'Afternoon-Monitor',
    'AutoBackup5min',
    'Final-Backup'
)

$ok = 0; $fail = 0

foreach ($name in $targetTasks) {
    try {
        $task = Get-ScheduledTask -TaskName $name -ErrorAction Stop
        $settings = $task.Settings
        $settings.Hidden = $true
        Set-ScheduledTask -TaskName $name -Settings $settings -ErrorAction Stop | Out-Null
        Write-Host "  [OK] $name" -ForegroundColor Green
        $ok++
    } catch {
        Write-Host "  [SKIP] $name : $($_.Exception.Message)" -ForegroundColor Yellow
        $fail++
    }
}

# BridgeBlogAuto: BAT file cannot be hidden directly -> wrap with VBS
$vbsPath = "Q:\Claudework\ClaudeBlog\run_silent.vbs"
$vbsContent = 'Set WshShell = CreateObject("WScript.Shell")' + [Environment]::NewLine
$vbsContent += 'WshShell.Run "Q:\Claudework\ClaudeBlog\run_scheduled.bat", 0, False'
Set-Content -Path $vbsPath -Value $vbsContent -Encoding ASCII
Write-Host "  [VBS] run_silent.vbs created" -ForegroundColor Cyan

try {
    $task = Get-ScheduledTask -TaskName 'BridgeBlogAuto' -ErrorAction Stop
    $action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$vbsPath`""
    $settings = $task.Settings
    $settings.Hidden = $true
    Set-ScheduledTask -TaskName 'BridgeBlogAuto' -Action $action -Settings $settings -ErrorAction Stop | Out-Null
    Write-Host "  [OK] BridgeBlogAuto -> VBS wrapper applied" -ForegroundColor Green
    $ok++
} catch {
    Write-Host "  [FAIL] BridgeBlogAuto : $($_.Exception.Message)" -ForegroundColor Red
    $fail++
}

Write-Host ""
Write-Host "Done: OK=$ok  SKIP/FAIL=$fail" -ForegroundColor White
Write-Host "Blue windows will not appear on next reboot." -ForegroundColor Cyan
