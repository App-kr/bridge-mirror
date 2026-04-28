$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== WMI Win32_ProcessStartTrace - 60s real-time tracking ==="
Write-Host "Watching cmd/powershell/conhost spawn with parent details"
Write-Host ""

$results = @{}
$details = @()
$startTime = Get-Date

# WMI ProcessStartTrace 이벤트 등록
$query = "SELECT * FROM Win32_ProcessStartTrace WHERE ProcessName='cmd.exe' OR ProcessName='powershell.exe' OR ProcessName='conhost.exe' OR ProcessName='git.exe' OR ProcessName='gh.exe' OR ProcessName='tasklist.exe'"

Register-WmiEvent -Query $query -SourceIdentifier "BridgeSpawnTrace" -Action {
    $event = $Event.SourceEventArgs.NewEvent
    $childPid = $event.ProcessID
    $parentPid = $event.ParentProcessID
    $childName = $event.ProcessName

    $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$parentPid" -ErrorAction SilentlyContinue
    $parentName = if ($parent) { $parent.Name } else { 'GONE' }
    $parentCmd = if ($parent -and $parent.CommandLine) {
        $parent.CommandLine.Substring(0,[Math]::Min(120,$parent.CommandLine.Length))
    } else { '' }

    $key = "$childName <- $parentName"
    $script:results = $script:results
    if (-not $script:results.ContainsKey($key)) { $script:results[$key] = 0 }
    $script:results[$key]++

    if ($script:details.Count -lt 50) {
        $script:details += [PSCustomObject]@{
            Time = (Get-Date).ToString("HH:mm:ss.fff")
            Child = "$childName(PID $childPid)"
            Parent = "$parentName(PID $parentPid)"
            ParentCmd = $parentCmd
        }
    }
} | Out-Null

Start-Sleep -Seconds 60

Unregister-Event -SourceIdentifier "BridgeSpawnTrace"

Write-Host "=== Spawn aggregate (60s) ==="
$results.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object {
    Write-Host ("  {0,4}x  {1}" -f $_.Value, $_.Key)
}
$total = ($results.Values | Measure-Object -Sum).Sum
Write-Host ("`nTotal: {0} | Rate: {1}/s" -f $total, [math]::Round($total / 60.0, 2))

Write-Host ""
Write-Host "=== First 30 spawn events with parent CommandLine ==="
$details | Select-Object -First 30 | ForEach-Object {
    Write-Host ("[{0}] {1} <- {2}" -f $_.Time, $_.Child, $_.Parent)
    if ($_.ParentCmd) { Write-Host ("    {0}" -f $_.ParentCmd) }
}
