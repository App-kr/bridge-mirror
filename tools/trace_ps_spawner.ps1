$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== powershell.exe new spawn capture (15s) ==="
$captured = @{}
$end = (Get-Date).AddSeconds(15)
while ((Get-Date) -lt $end) {
    Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | ForEach-Object {
        if (-not $captured.ContainsKey($_.ProcessId)) {
            $captured[$_.ProcessId] = $_
        }
    }
    Start-Sleep -Milliseconds 200
}

Write-Host ("Captured {0} new powershell.exe in 15s" -f $captured.Count)
Write-Host ""

$parents = @{}
foreach ($p in $captured.Values) {
    $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($p.ParentProcessId)" -ErrorAction SilentlyContinue
    $pname = if ($parent) { $parent.Name } else { 'GONE' }
    $pcmd = if ($parent -and $parent.CommandLine) { $parent.CommandLine.Substring(0,[Math]::Min(150,$parent.CommandLine.Length)) } else { '' }
    $key = "$pname"
    if (-not $parents.ContainsKey($key)) {
        $parents[$key] = @{ count = 0; sample_cmd = $pcmd; child_cmds = @() }
    }
    $parents[$key].count++
    $childCmd = if ($p.CommandLine) { $p.CommandLine.Substring(0,[Math]::Min(120,$p.CommandLine.Length)) } else { '' }
    if ($parents[$key].child_cmds.Count -lt 2) {
        $parents[$key].child_cmds += $childCmd
    }
}

Write-Host "=== Top powershell.exe parents ==="
$parents.GetEnumerator() | Sort-Object { $_.Value.count } -Descending | ForEach-Object {
    Write-Host ""
    Write-Host ("  [{0}x]  PARENT: {1}" -f $_.Value.count, $_.Key)
    Write-Host ("    parent cmd: {0}" -f $_.Value.sample_cmd)
    foreach ($cc in $_.Value.child_cmds) {
        Write-Host ("    child cmd:  {0}" -f $cc)
    }
}
