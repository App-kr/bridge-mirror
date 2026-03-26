$bridgeTasks = @('Afternoon-Monitor', 'AutoBackup5min', 'Final-Backup')
foreach ($name in $bridgeTasks) {
    try {
        $task = Get-ScheduledTask -TaskPath '\Bridge\' -TaskName $name -ErrorAction Stop
        $settings = $task.Settings
        $settings.Hidden = $true
        Set-ScheduledTask -TaskPath '\Bridge\' -TaskName $name -Settings $settings -ErrorAction Stop | Out-Null
        Write-Host "[OK] $name"
    } catch {
        Write-Host "[FAIL] $name : $($_.Exception.Message)"
    }
}
Write-Host "Bridge subfolder tasks done."
