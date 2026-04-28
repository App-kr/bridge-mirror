$ErrorActionPreference = 'SilentlyContinue'

Write-Host "=== 30s spawn rate (after ctypes fix) ==="
$seen = @{}
$culprits = @{}
$end = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $end) {
    Get-CimInstance Win32_Process -Filter "Name='cmd.exe' OR Name='powershell.exe' OR Name='conhost.exe' OR Name='git.exe' OR Name='gh.exe' OR Name='tasklist.exe'" | ForEach-Object {
        if (-not $seen.ContainsKey($_.ProcessId)) {
            $seen[$_.ProcessId] = $true
            $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.ParentProcessId)"
            $pname = if ($parent) { $parent.Name } else { 'GONE' }
            $key = "$($_.Name) <- $pname"
            if (-not $culprits.ContainsKey($key)) { $culprits[$key] = 0 }
            $culprits[$key]++
        }
    }
    Start-Sleep -Milliseconds 250
}

Write-Host "`n=== Top spawn patterns (30s) ==="
$culprits.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 10 | ForEach-Object {
    Write-Host ("  {0,3}x  {1}" -f $_.Value, $_.Key)
}
Write-Host ("`nTotal: {0} | Rate: {1}/s" -f $seen.Count, [math]::Round($seen.Count / 30.0, 2))
Write-Host "(이전: 112개 / 3.73/s -- 목표: 1/s 미만)"
