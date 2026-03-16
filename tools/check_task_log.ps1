# Check Task Scheduler logs more broadly
Write-Host "--- TaskScheduler/Operational log status ---"
$log = Get-WinEvent -ListLog "Microsoft-Windows-TaskScheduler/Operational" -ErrorAction SilentlyContinue
if ($log) {
    Write-Host "Log enabled: $($log.IsEnabled)"
    Write-Host "Log size: $($log.FileSize) bytes"
    Write-Host "Record count: $($log.RecordCount)"
}

Write-Host ""
Write-Host "--- TaskScheduler errors (last 48h) ---"
Get-WinEvent -LogName "Microsoft-Windows-TaskScheduler/Operational" -MaxEvents 500 -ErrorAction SilentlyContinue |
    Where-Object { $_.Id -in @(101,103,111,201,202,203) -and $_.TimeCreated -gt (Get-Date).AddDays(-2) } |
    Select-Object TimeCreated, Id, @{N="TaskName";E={$_.Properties[0].Value}}, @{N="Result";E={$_.Properties[1].Value}} |
    Sort-Object TimeCreated -Descending | Select-Object -First 20 | Format-Table -AutoSize

Write-Host ""
Write-Host "--- AudioAutoSwitcher last run info ---"
$info = Get-ScheduledTaskInfo -TaskName "AudioAutoSwitcher" -ErrorAction SilentlyContinue
if ($info) {
    Write-Host "LastRun: $($info.LastRunTime)"
    Write-Host "LastResult: $($info.LastTaskResult) (0=success, non-zero=fail)"
    Write-Host "NextRun: $($info.NextRunTime)"
    Write-Host "NumberOfMissedRuns: $($info.NumberOfMissedRuns)"
}

Write-Host ""
Write-Host "--- AudioSwitcher last run info ---"
$info2 = Get-ScheduledTaskInfo -TaskName "AudioSwitcher" -ErrorAction SilentlyContinue
if ($info2) {
    Write-Host "LastRun: $($info2.LastRunTime)"
    Write-Host "LastResult: $($info2.LastTaskResult)"
}
