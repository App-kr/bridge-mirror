# register_audio_task.ps1 - Task Scheduler registration (requires admin)

$taskName   = "SpeakerDefaultOnLogon"
$scriptPath = "Q:\Claudework\bridge base\tools\fix_audio_default.ps1"
$userName   = $env:USERNAME

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$trigger  = New-ScheduledTaskTrigger -AtLogOn -User $userName
$action   = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument ("-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"" + $scriptPath + "`" -Silent")
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName  $taskName `
    -Trigger   $trigger `
    -Action    $action `
    -Settings  $settings `
    -RunLevel  Highest `
    -Force | Out-Null

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    Write-Host ("OK: Task registered - " + $taskName)
    Write-Host ("State: " + $task.State)
} else {
    Write-Host "FAIL: Run as Administrator"
}
