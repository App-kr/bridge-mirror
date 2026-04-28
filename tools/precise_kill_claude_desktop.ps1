$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Claude process classification (23 instances expected) ==="
$all = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'Claude.exe' -or $_.Name -eq 'claude.exe' }

$desktop = @()
$cli     = @()
$other   = @()

foreach ($p in $all) {
    if ($p.ExecutablePath -like '*WindowsApps\Claude_*') {
        $desktop += $p
    } elseif ($p.ExecutablePath -like '*claude-code*') {
        $cli += $p
    } else {
        $other += $p
    }
}

Write-Host ("  Desktop app (KILL target): {0}" -f $desktop.Count)
Write-Host ("  Claude Code CLI (PROTECT): {0}" -f $cli.Count)
Write-Host ("  Other:                     {0}" -f $other.Count)

Write-Host ""
Write-Host "=== Killing desktop app processes ==="
$totalRam = 0
foreach ($p in $desktop) {
    $ram = [math]::Round($p.WorkingSetSize/1MB, 1)
    $totalRam += $ram
    Write-Host ("  KILL PID={0} RAM={1}MB" -f $p.ProcessId, $ram)
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Write-Host ("Total RAM reclaim target: {0} MB" -f [math]::Round($totalRam, 1))

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "=== Verify (re-kill if any survived) ==="
$still = Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -like '*WindowsApps\Claude_*'
}
if ($still) {
    Write-Host ("  WARN: {0} survivors - force re-kill" -f $still.Count)
    foreach ($p in $still) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "  OK: desktop app fully terminated"
}

Write-Host ""
Write-Host "=== Protected Claude Code CLI (still running) ==="
foreach ($p in $cli) {
    Write-Host ("  PID={0} RAM={1}MB" -f $p.ProcessId, [math]::Round($p.WorkingSetSize/1MB, 1))
}

Write-Host ""
Write-Host "=== Memory after ==="
$os = Get-CimInstance Win32_OperatingSystem
$used = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB, 1)
$total = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
Write-Host ("  Used: {0} GB / {1} GB ({2}%)" -f $used, $total, [math]::Round($used/$total*100, 1))
