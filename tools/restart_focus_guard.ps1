$ErrorActionPreference = 'SilentlyContinue'
Write-Host "=== Killing existing focus_guard processes ==="
Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like '*focus_guard.py*'
} | ForEach-Object {
    Write-Host ("  KILL PID={0}" -f $_.ProcessId)
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1

Write-Host "`n=== Starting new BRIDGE_FocusGuard ==="
Start-ScheduledTask -TaskName 'BRIDGE_FocusGuard'
Start-Sleep -Seconds 2

$running = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*focus_guard.py*' }
foreach ($p in $running) {
    Write-Host ("  RUNNING PID={0} mem={1}MB" -f $p.ProcessId, [math]::Round($p.WorkingSetSize/1MB,1))
}
if (-not $running) { Write-Host "  WARN: focus_guard not detected" }
