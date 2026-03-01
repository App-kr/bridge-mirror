# BRIDGE RPA Scheduler Setup - 6hr cycle, 10 posts/run
Unregister-ScheduledTask -TaskName "BRIDGE_RPA_Daemon" -Confirm:$false -ErrorAction SilentlyContinue

$action   = New-ScheduledTaskAction -Execute "Q:\Claudework\bridge base\run_rpa.bat"
$trigger  = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Hours 6) -Once -At (Get-Date)
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 60)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -RunLevel Highest

Register-ScheduledTask -TaskName "BRIDGE_RPA_Daemon" `
    -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force | Out-Null

$t = Get-ScheduledTask -TaskName "BRIDGE_RPA_Daemon"
Write-Host "Task:     $($t.TaskName)"
Write-Host "State:    $($t.State)"
Write-Host "Interval: 6 hours (360 min)"
Write-Host "Limit:    10 posts per run"
Write-Host "Action:   $($t.Actions[0].Execute)"
Write-Host ""
Write-Host "OK - Scheduled: 10 posts every 6 hours"
