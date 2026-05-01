$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== WMI Win32_ProcessStartTrace - real-time (no GONE) ==="
Write-Host "Captures parent at spawn instant - 30s"
Write-Host ""

$query = @"
SELECT * FROM Win32_ProcessStartTrace
WHERE ProcessName='git.exe' OR ProcessName='conhost.exe' OR
      ProcessName='cmd.exe' OR ProcessName='powershell.exe' OR
      ProcessName='wmic.exe' OR ProcessName='tasklist.exe' OR
      ProcessName='schtasks.exe'
"@

$watcher = New-Object System.Management.ManagementEventWatcher($query)
$watcher.Options.Timeout = [System.TimeSpan]::FromSeconds(30)

$counts = @{}
$end = (Get-Date).AddSeconds(30)

try {
    $watcher.Start()
    while ((Get-Date) -lt $end) {
        try {
            $event = $watcher.WaitForNextEvent()
            if (-not $event) { break }
            $childPid = $event.ProcessID
            $parentPid = $event.ParentProcessID
            $childName = $event.ProcessName

            # 즉시 부모 정보 capture (still alive)
            $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$parentPid" -ErrorAction SilentlyContinue
            $pname = if ($parent) { $parent.Name } else { 'GONE' }
            $pcmd = if ($parent -and $parent.CommandLine) { $parent.CommandLine.Substring(0,[Math]::Min(120,$parent.CommandLine.Length)) } else { '' }

            $key = "$childName <- $pname"
            if (-not $counts.ContainsKey($key)) { $counts[$key] = @{ count=0; samples=@() } }
            $counts[$key].count++
            if ($counts[$key].samples.Count -lt 2 -and $pcmd) {
                $counts[$key].samples += $pcmd
            }
        } catch [System.Management.ManagementException] {
            break
        }
    }
} finally {
    $watcher.Stop()
    $watcher.Dispose()
}

Write-Host "=== Top spawners (real-time WMI) ==="
$counts.GetEnumerator() | Sort-Object { $_.Value.count } -Descending | ForEach-Object {
    Write-Host ""
    Write-Host ("  [{0}x] {1}" -f $_.Value.count, $_.Key)
    foreach ($s in $_.Value.samples) { Write-Host "    parent: $s" }
}
$total = ($counts.Values | ForEach-Object { $_.count } | Measure-Object -Sum).Sum
Write-Host ""
Write-Host ("Total spawn events in 30s: {0}" -f $total)
