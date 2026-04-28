$ErrorActionPreference = 'SilentlyContinue'

$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*focus_guard.py*' } |
    Sort-Object CreationDate -Descending  # newest first

if ($procs.Count -le 1) {
    Write-Host "OK: $($procs.Count) instance(s) running"
    exit 0
}

Write-Host "Found $($procs.Count) focus_guard instances - keeping newest, killing the rest"
$keep = $procs[0]
Write-Host "  KEEP PID=$($keep.ProcessId)"

foreach ($p in $procs[1..($procs.Count-1)]) {
    Write-Host "  KILL PID=$($p.ProcessId)"
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}

# Set MultipleInstances policy to prevent re-occurrence
try {
    $task = Get-ScheduledTask -TaskName "BRIDGE_FocusGuard" -ErrorAction Stop
    $task.Settings.MultipleInstances = 'IgnoreNew'
    Set-ScheduledTask -TaskName "BRIDGE_FocusGuard" -Settings $task.Settings | Out-Null
    Write-Host "OK: MultipleInstances policy = IgnoreNew"
} catch {
    Write-Host "WARN: Could not update task policy - $_"
}
