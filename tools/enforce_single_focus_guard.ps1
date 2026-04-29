$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Killing ALL focus_guard instances ==="
$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*focus_guard.py*' } |
         Sort-Object CreationDate
foreach ($p in $procs) {
    Write-Host ("  KILL PID={0} (age={1}m)" -f $p.ProcessId, [math]::Round(((Get-Date)-$p.CreationDate).TotalMinutes,1))
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "=== Force MultipleInstances=IgnoreNew on all 4 daemons ==="
@('BRIDGE_FocusGuard','BRIDGE_RAMWatchdog','BRIDGE_GameModeGuardian','BRIDGE_IOWatchdog') | ForEach-Object {
    try {
        $task = Get-ScheduledTask -TaskName $_ -ErrorAction Stop
        if ($task.Settings.MultipleInstances -ne 'IgnoreNew') {
            $task.Settings.MultipleInstances = 'IgnoreNew'
            Set-ScheduledTask -TaskName $_ -Settings $task.Settings | Out-Null
            Write-Host ("  POLICY-FIX: $_ -> IgnoreNew")
        } else {
            Write-Host ("  OK:         $_ (already IgnoreNew)")
        }
    } catch {
        Write-Host ("  SKIP: $_ - $($_.Exception.Message)")
    }
}

Write-Host ""
Write-Host "=== Cleanup duplicate ram_watchdog / game_mode / io_watchdog too ==="
@('ram_watchdog.py','game_mode_guardian.py','io_watchdog.py') | ForEach-Object {
    $pattern = $_
    $procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*$pattern*" } |
             Sort-Object CreationDate -Descending
    if ($procs.Count -gt 1) {
        Write-Host ("  Multiple $pattern : keep newest, kill {0}" -f ($procs.Count - 1))
        $keep = $procs[0]
        foreach ($p in $procs[1..($procs.Count-1)]) {
            Write-Host ("    KILL PID={0}" -f $p.ProcessId)
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
}

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "=== Restart FocusGuard (single instance) ==="
Start-ScheduledTask -TaskName 'BRIDGE_FocusGuard'
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "=== Final daemon state ==="
Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like '*focus_guard.py*' -or
    $_.CommandLine -like '*ram_watchdog.py*' -or
    $_.CommandLine -like '*game_mode_guardian.py*' -or
    $_.CommandLine -like '*io_watchdog.py*'
} | Select-Object ProcessId,
    @{N='daemon';E={
        if($_.CommandLine -like '*focus_guard*'){'focus_guard'}
        elseif($_.CommandLine -like '*ram_watchdog*'){'ram_watchdog'}
        elseif($_.CommandLine -like '*game_mode*'){'game_mode'}
        else{'io_watchdog'}
    }},
    @{N='age_s';E={[math]::Round(((Get-Date)-$_.CreationDate).TotalSeconds,1)}} |
    Format-Table -AutoSize
