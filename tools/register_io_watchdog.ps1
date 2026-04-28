$ErrorActionPreference = 'Stop'
$pythonw = "Q:\Phtyon 3\pythonw.exe"
$script = "Q:\Claudework\bridge base\tools\io_watchdog.py"

$action = New-ScheduledTaskAction -Execute $pythonw -Argument "-X utf8 `"$script`""
$trigger = New-ScheduledTaskTrigger -AtLogon
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -Hidden `
    -ExecutionTimeLimit (New-TimeSpan -Days 365) `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew

Unregister-ScheduledTask -TaskName "BRIDGE_IOWatchdog" -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName "BRIDGE_IOWatchdog" `
    -Action $action -Trigger $trigger -Settings $settings `
    -Description "Disk IO spike detector (RULE-7 enforcement)" `
    -RunLevel Limited | Out-Null
Write-Host "OK: BRIDGE_IOWatchdog registered"

Start-ScheduledTask -TaskName 'BRIDGE_IOWatchdog'
Start-Sleep -Seconds 2
$proc = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*io_watchdog.py*' } | Select-Object -First 1
if ($proc) { Write-Host ("OK: PID={0} running" -f $proc.ProcessId) }
