$ErrorActionPreference = 'Stop'
$pythonw = "Q:\Phtyon 3\pythonw.exe"
$script = "Q:\Claudework\bridge base\tools\amtlib_guardian.py"

$action = New-ScheduledTaskAction -Execute $pythonw -Argument "-X utf8 `"$script`""
$trigger = New-ScheduledTaskTrigger -AtLogon
$rep = (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration (New-TimeSpan -Days 365)).Repetition
$trigger.Repetition = $rep
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable -Hidden -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -MultipleInstances IgnoreNew

Unregister-ScheduledTask -TaskName 'BRIDGE_AmtlibGuardian' -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName 'BRIDGE_AmtlibGuardian' -Action $action -Trigger $trigger -Settings $settings -Description 'Adobe amtlib.dll permanent protection - 30min check' -RunLevel Limited | Out-Null
Write-Host "OK: BRIDGE_AmtlibGuardian registered (every 30min)"

Start-ScheduledTask -TaskName 'BRIDGE_AmtlibGuardian'
Start-Sleep 2
$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*amtlib_guardian.py*' } | Select-Object -First 1
if ($p) { Write-Host ("Running PID=" + $p.ProcessId) }
