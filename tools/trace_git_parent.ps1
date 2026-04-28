$ErrorActionPreference = 'SilentlyContinue'

Write-Host "=== Watching git.exe spawn over 20 seconds (find parent) ==="
$seen = @{}
$culprits = @{}
$end = (Get-Date).AddSeconds(20)
while ((Get-Date) -lt $end) {
    Get-CimInstance Win32_Process -Filter "Name='git.exe'" | ForEach-Object {
        if (-not $seen.ContainsKey($_.ProcessId)) {
            $seen[$_.ProcessId] = $true
            $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.ParentProcessId)"
            $pname = if ($parent) { $parent.Name } else { 'UNKNOWN' }
            $pcmd = if ($parent -and $parent.CommandLine) {
                $parent.CommandLine.Substring(0,[Math]::Min(80,$parent.CommandLine.Length))
            } else { '' }
            $key = "$pname"
            if (-not $culprits.ContainsKey($key)) {
                $culprits[$key] = @{count=0; sample_cmd=$pcmd}
            }
            $culprits[$key].count++
        }
    }
    Start-Sleep -Milliseconds 200
}

Write-Host "`n=== Top spawners of git.exe (20s window) ==="
$culprits.GetEnumerator() | Sort-Object { $_.Value.count } -Descending | ForEach-Object {
    Write-Host ("  {0,-30} count={1}  parentcmd: {2}" -f $_.Key, $_.Value.count, $_.Value.sample_cmd)
}

Write-Host "`n=== Total git.exe spawned in 20s: $($seen.Count) ==="
Write-Host "Rate: $([math]::Round($seen.Count / 20.0, 2)) per second"
