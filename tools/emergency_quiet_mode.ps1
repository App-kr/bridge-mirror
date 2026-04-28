$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Emergency quiet mode - disable ALL non-essential BRIDGE tasks
# Survives only: focus_guard, ram_watchdog, game_mode_guardian, api server, db_sync

$DISABLE = @(
    'BridgeWorkTracker',
    'BRIDGE_GDrive_Backup',
    'BRIDGE_GDrive_Backup_Frequent',
    'BRIDGE_EmailAutoresponder',
    'BRIDGE_EmailAutoresponder_Night',
    'BRIDGE_EmailReporter',
    'ClaudeBlog_AutoBackup',
    'BRIDGE_IOC_Watcher',
    'BRIDGE_Render_Keepalive',
    'BRIDGE_DB_Backup',
    'BRIDGE_Behavior_Check',
    'BRIDGE_Auto_Security_Patch',
    'BRIDGE_ThreatFeed_Sync',
    'ClaudeworkAutoRestore',
    'BridgeBlogAuto',
    'MatjokdoDaily',
    'TeastPost30Day',
    'AudioAutoSwitcher',
    'BridgeAudioStartup',
    'ClaudeBlog_monthly_kw',
    'BridgeRenderMonitor',
    'BridgeSecurityAudit',
    'BridgeSpeakerDefault',
    'SpeakerDefaultOnLogon',
    'BRIDGE_FieldKeyTester',
    'ABKO_N460_AutoConnect',
    'ABKO_N460_StartupMonitor',
    'HeadsetManager',
    'ChromeCleanSearchEngines',
    'BridgeInterviewReminder',
    'BridgeCraigslistRPA',
    'BridgeLogRotation',
    'Bridge_DDNS_Watchdog',
    'BridgeTelegramBot',
    'QDriveBackupDaemon'
)

# 백업 폴더에 현재 상태 저장 (롤백용)
$bakDir = "Q:\Claudework\bridge base\.backups\quiet_mode_state"
New-Item -ItemType Directory -Force -Path $bakDir | Out-Null
$stateFile = Join-Path $bakDir ("disabled_" + (Get-Date -Format 'yyyyMMdd_HHmmss') + ".json")
$disabledList = @()

foreach ($name in $DISABLE) {
    try {
        $task = Get-ScheduledTask -TaskName $name -ErrorAction Stop
        if ($task.State -ne 'Disabled') {
            Disable-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue | Out-Null
            $disabledList += $name
            Write-Host ("  DISABLED: {0}" -f $name)
        } else {
            Write-Host ("  already-off: {0}" -f $name)
        }
    } catch {
        # task not found - skip
    }
}

# Bridge\* subfolder
foreach ($name in @('AutoBackup5min','Afternoon-Monitor','Final-Backup','DBSyncDaemon')) {
    try {
        $task = Get-ScheduledTask -TaskName $name -TaskPath '\Bridge\' -ErrorAction Stop
        if ($task.State -ne 'Disabled' -and $name -ne 'DBSyncDaemon') {  # DBSync는 보호
            Disable-ScheduledTask -TaskName $name -TaskPath '\Bridge\' -ErrorAction SilentlyContinue | Out-Null
            $disabledList += "\Bridge\$name"
            Write-Host ("  DISABLED: \Bridge\{0}" -f $name)
        }
    } catch {}
}

$disabledList | ConvertTo-Json | Out-File $stateFile -Encoding utf8
Write-Host ""
Write-Host ("=== State saved to {0} ({1} tasks disabled) ===" -f $stateFile, $disabledList.Count)
Write-Host ""
Write-Host "PROTECTED (still running):"
Write-Host "  - BRIDGE_FocusGuard (focus protection)"
Write-Host "  - BRIDGE_RAMWatchdog (memory cleanup)"
Write-Host "  - BRIDGE_GameModeGuardian (game mode)"
Write-Host "  - \Bridge\DBSyncDaemon (DB sync)"
Write-Host ""
Write-Host "To rollback later: Get-Content $stateFile | ConvertFrom-Json | ForEach-Object { Enable-ScheduledTask -TaskName \$_ }"
