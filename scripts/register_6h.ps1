$PS1   = "Q:\Claudework\bridge base\scripts\run_craigslist_rpa.ps1"
$BASE  = "Q:\Claudework\bridge base"

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument ('-WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $PS1 + '"') `
    -WorkingDirectory $BASE

$trig = New-ScheduledTaskTrigger `
    -Once -At (Get-Date).AddHours(6) `
    -RepetitionInterval (New-TimeSpan -Hours 6) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable

$principal = New-ScheduledTaskPrincipal `
    -UserId ([Environment]::UserName) `
    -LogonType Interactive `
    -RunLevel Highest

Unregister-ScheduledTask -TaskName "BridgeCraigslistRPA_6H" -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName "BridgeCraigslistRPA_6H" `
    -Action $action `
    -Trigger $trig `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

$t = Get-ScheduledTask -TaskName "BridgeCraigslistRPA_6H" -ErrorAction SilentlyContinue
if ($t) { Write-Host ("OK: BridgeCraigslistRPA_6H State=" + $t.State) }
else    { Write-Host "FAIL: task not created" }
