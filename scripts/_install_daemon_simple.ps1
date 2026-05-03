$taskName  = 'BRIDGE_EmailAutoresponder_Daemon'
$pythonExe = 'Q:\Phtyon 3\pythonw.exe'
$script    = 'Q:\Claudework\bridge base\tools\email_autoresponder.py'
$workDir   = 'Q:\Claudework\bridge base'

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction -Execute "`"$pythonExe`"" -Argument "-X utf8 `"$script`" --force" -WorkingDirectory $workDir
$triggers = @((New-ScheduledTaskTrigger -AtLogOn), (New-ScheduledTaskTrigger -AtStartup))
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartInterval (New-TimeSpan -Minutes 1) -RestartCount 9999 -ExecutionTimeLimit (New-TimeSpan -Days 3650) -MultipleInstances IgnoreNew -Hidden
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

try {
  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $triggers -Settings $settings -Principal $principal -Description "Hidden daemon (10min poll)" -ErrorAction Stop | Out-Null
  Write-Host "[OK] Task registered"
  Start-ScheduledTask -TaskName $taskName
  Write-Host "[OK] Task started"
} catch {
  Write-Host "[ERR] $($_.Exception.Message)"
}
