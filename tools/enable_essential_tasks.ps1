$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ESSENTIAL = @(
    @{ Name='BRIDGE_DB_Backup';            Path='\';        Reason='DB backup' }
    @{ Name='BRIDGE_GDrive_Backup';        Path='\';        Reason='Cloud backup' }
    @{ Name='BRIDGE_IOC_Watcher';          Path='\';        Reason='Security IOC' }
    @{ Name='BRIDGE_Behavior_Check';       Path='\';        Reason='Anomaly detect' }
    @{ Name='BRIDGE_Auto_Security_Patch';  Path='\';        Reason='Auto patch' }
    @{ Name='BRIDGE_ThreatFeed_Sync';      Path='\';        Reason='Threat feed' }
    @{ Name='BridgeTelegramBot';           Path='\';        Reason='User alerts' }
    @{ Name='BRIDGE_EmailAutoresponder';   Path='\';        Reason='Email reply' }
    @{ Name='AutoBackup5min';              Path='\Bridge\'; Reason='Frequent backup' }
    @{ Name='Final-Backup';                Path='\Bridge\'; Reason='Daily backup' }
)

Write-Host "=== Re-enabling 10 essential tasks (with Hidden enforcement) ==="
$enabled = 0
foreach ($t in $ESSENTIAL) {
    try {
        $task = Get-ScheduledTask -TaskName $t.Name -TaskPath $t.Path -ErrorAction Stop
        if (-not $task.Settings.Hidden) {
            $task.Settings.Hidden = $true
            Set-ScheduledTask -TaskName $t.Name -TaskPath $t.Path -Settings $task.Settings | Out-Null
            Write-Host ("  HIDDEN-FORCE: {0}{1}" -f $t.Path, $t.Name)
        }
        Enable-ScheduledTask -TaskName $t.Name -TaskPath $t.Path -ErrorAction Stop | Out-Null
        $enabled++
        Write-Host ("  ENABLED: {0}{1}  ({2})" -f $t.Path, $t.Name, $t.Reason)
        foreach ($a in $task.Actions) {
            if ($a.Execute -match 'cmd\.exe$' -or $a.Execute -match '\.bat$') {
                Write-Host "    WARN: cmd/bat direct call - verify Hidden wrapper"
            }
        }
    } catch {
        Write-Host ("  SKIP: {0}{1} - {2}" -f $t.Path, $t.Name, $_.Exception.Message)
    }
}
Write-Host ""
Write-Host ("Result: {0} enabled" -f $enabled)
