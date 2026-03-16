# Check triggers for all tasks - especially logon triggers
$tasks = Get-ScheduledTask -ErrorAction SilentlyContinue

Write-Host "=== Tasks with LOGON triggers ==="
foreach ($t in $tasks) {
    $logonTriggers = $t.Triggers | Where-Object { $_.GetType().Name -match "LogonTrigger|CimInstance" -and $_.ToString() -match "Logon|Boot" }

    # Also check by CIM class
    $trigStr = $t.Triggers | ForEach-Object { $_.ToString() }
    $hasLogon = ($t.Triggers | Where-Object { $_ -match "MSFT_TaskLogonTrigger|Boot" }).Count -gt 0

    if ($hasLogon) {
        Write-Host "Task: $($t.TaskName) [State: $($t.State)]"
        foreach ($action in $t.Actions) {
            Write-Host "  Execute: $($action.Execute)"
            Write-Host "  Args:    $($action.Arguments)"
        }
        Write-Host ""
    }
}

Write-Host ""
Write-Host "=== ALL task triggers (simple) ==="
foreach ($t in $tasks) {
    if ($t.TaskName -match "Audio|Bridge|Craig|RPA|Tracker|Monitor|Backup") {
        Write-Host "Task: $($t.TaskName)"
        Write-Host "  State: $($t.State)"
        foreach ($tr in $t.Triggers) {
            Write-Host "  Trigger type: $($tr.GetType().Name)"
            if ($tr.PSObject.Properties['TriggerType']) {
                Write-Host "  TriggerType: $($tr.TriggerType)"
            }
        }
        foreach ($a in $t.Actions) {
            Write-Host "  Execute: $($a.Execute)"
            Write-Host "  Args:    $($a.Arguments)"
        }
        Write-Host ""
    }
}
