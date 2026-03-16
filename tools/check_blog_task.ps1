$task = Get-ScheduledTask -TaskName "BridgeBlogAuto"
$info = Get-ScheduledTaskInfo -TaskName "BridgeBlogAuto"

Write-Host "=== BridgeBlogAuto Task ==="
Write-Host "State: $($task.State)"
Write-Host "Last Run: $($info.LastRunTime)"
Write-Host "Last Result: $($info.LastTaskResult)"
Write-Host "Next Run: $($info.NextRunTime)"
Write-Host ""
Write-Host "=== Actions ==="
foreach ($action in $task.Actions) {
    Write-Host "Execute: $($action.Execute)"
    Write-Host "Arguments: $($action.Arguments)"
    Write-Host "WorkDir: $($action.WorkingDirectory)"
}
Write-Host ""
Write-Host "=== Triggers ==="
foreach ($trigger in $task.Triggers) {
    Write-Host "Type: $($trigger.CimClass.CimClassName)"
    Write-Host "Enabled: $($trigger.Enabled)"
    if ($trigger.StartBoundary) { Write-Host "Start: $($trigger.StartBoundary)" }
}
