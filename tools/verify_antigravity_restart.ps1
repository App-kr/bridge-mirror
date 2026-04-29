$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== A) Antigravity processes after restart ==="
$ag = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '*Antigravity*' }
if (-not $ag) {
    Write-Host "  Antigravity NOT running yet (still loading?)"
} else {
    $totalRam = 0
    $oldest = $null
    foreach ($p in $ag) {
        $totalRam += $p.WorkingSetSize
        $age = ((Get-Date) - $p.CreationDate).TotalMinutes
        if (-not $oldest -or $age -gt $oldest) { $oldest = $age }
    }
    Write-Host ("  Process count: {0}" -f $ag.Count)
    Write-Host ("  Total RAM:     {0} MB" -f [math]::Round($totalRam/1MB,1))
    Write-Host ("  Oldest age:    {0:F1} min (smaller = recent restart)" -f $oldest)
}

Write-Host ""
Write-Host "=== B) Top RAM consumers (system-wide) ==="
Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 8 |
    Select-Object Name, Id, @{N='RAM_MB';E={[math]::Round($_.WorkingSet/1MB,1)}} |
    Format-Table -AutoSize

Write-Host ""
Write-Host "=== C) Big node.exe LSP/dev servers ==="
Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
    Where-Object { $_.WorkingSetSize -gt 100MB } |
    Sort-Object WorkingSetSize -Descending |
    ForEach-Object {
        $cmdShort = if ($_.CommandLine) { $_.CommandLine.Substring(0,[Math]::Min(150,$_.CommandLine.Length)) } else { '' }
        [PSCustomObject]@{
            PID = $_.ProcessId
            RAM_MB = [math]::Round($_.WorkingSetSize/1MB,1)
            CMD = $cmdShort
        }
    } | Format-Table -AutoSize -Wrap

Write-Host ""
Write-Host "=== D) System memory ==="
$os = Get-CimInstance Win32_OperatingSystem
$used = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB, 1)
$total = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
Write-Host ("  RAM: {0} GB / {1} GB ({2}%)" -f $used, $total, [math]::Round($used/$total*100,1))

Write-Host ""
Write-Host "=== E) git.exe spawn rate (20s test - workspace settings effect) ==="
$seen = @{}
$end = (Get-Date).AddSeconds(20)
while ((Get-Date) -lt $end) {
    Get-CimInstance Win32_Process -Filter "Name='git.exe'" | ForEach-Object {
        if (-not $seen.ContainsKey($_.ProcessId)) {
            $seen[$_.ProcessId] = $true
        }
    }
    Start-Sleep -Milliseconds 200
}
Write-Host ("  git.exe spawned in 20s: {0}  ({1}/sec)" -f $seen.Count, [math]::Round($seen.Count/20.0, 2))
Write-Host "  (target: < 0.5/sec - workspace settings effective)"

Write-Host ""
Write-Host "=== F) Recent focus_guard hides (last 10) ==="
$logPath = "Q:\Claudework\bridge base\logs\focus_guard.jsonl"
Get-Content $logPath -Tail 10 -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $j = $_ | ConvertFrom-Json
        if ($j.event -like 'HIDDEN*') {
            Write-Host ("  {0} {1} pid={2}" -f $j.ts, $j.event, $j.pid)
        }
    } catch {}
}
