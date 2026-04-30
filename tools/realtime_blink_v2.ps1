$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== ALL spawn capture (60s, every PID) ==="
$captured = @{}
$end = (Get-Date).AddSeconds(60)
while ((Get-Date) -lt $end) {
    Get-CimInstance Win32_Process | ForEach-Object {
        if (-not $captured.ContainsKey($_.ProcessId)) {
            $captured[$_.ProcessId] = $_
        }
    }
    Start-Sleep -Milliseconds 100
}

# 처음부터 있던 것 제외 (60초 동안 새로 생긴 것만)
$baseline = New-Object System.Collections.Generic.HashSet[int]
Get-CimInstance Win32_Process | ForEach-Object { [void]$baseline.Add($_.ProcessId) }
# 위 baseline은 60초 후 - 즉 이미 살아있는 것 표시
# 실제 새 spawn은 위에서 캡처된 PID 중 baseline에서 PID 재사용 등 고려해야

# 단순화: capture 시작 후 새 부모 child 관계 식별
# 실제로 60초 후 살아있고 + 60초 전에는 없던 것
Write-Host ("Captured {0} processes during 60s (some pre-existing)" -f $captured.Count)
Write-Host ""

# console 관련만 보고
$consoleProcs = $captured.Values | Where-Object {
    $_.Name -in @('cmd.exe','powershell.exe','conhost.exe','pwsh.exe',
                  'wmic.exe','schtasks.exe','reg.exe','tasklist.exe')
}

Write-Host ("Console-related captures: {0}" -f $consoleProcs.Count)
$grouped = @{}
foreach ($p in $consoleProcs) {
    $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($p.ParentProcessId)" -ErrorAction SilentlyContinue
    $pname = if ($parent) { $parent.Name } else { 'GONE' }
    $key = "$($p.Name) <- $pname"
    if (-not $grouped.ContainsKey($key)) {
        $grouped[$key] = @{ count = 0; samples = @() }
    }
    $grouped[$key].count++
    if ($grouped[$key].samples.Count -lt 2) {
        $cmdShort = if ($p.CommandLine) { $p.CommandLine.Substring(0,[Math]::Min(120,$p.CommandLine.Length)) } else { '' }
        $pcmdShort = if ($parent -and $parent.CommandLine) { $parent.CommandLine.Substring(0,[Math]::Min(100,$parent.CommandLine.Length)) } else { '' }
        $grouped[$key].samples += "PID=$($p.ProcessId) cmd=$cmdShort | parent_cmd=$pcmdShort"
    }
}

$grouped.GetEnumerator() | Sort-Object { $_.Value.count } -Descending | ForEach-Object {
    Write-Host ""
    Write-Host ("[{0}x] {1}" -f $_.Value.count, $_.Key)
    foreach ($s in $_.Value.samples) {
        Write-Host ("    {0}" -f $s)
    }
}
