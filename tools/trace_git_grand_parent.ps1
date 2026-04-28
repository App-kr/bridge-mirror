$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== git.exe full ancestry (15s real spawn capture) ==="
$captured = @{}
$end = (Get-Date).AddSeconds(15)
while ((Get-Date) -lt $end) {
    Get-CimInstance Win32_Process -Filter "Name='git.exe'" | ForEach-Object {
        if (-not $captured.ContainsKey($_.ProcessId)) {
            $captured[$_.ProcessId] = $_
        }
    }
    Start-Sleep -Milliseconds 100
}

Write-Host ("Captured {0} unique git.exe in 15s`n" -f $captured.Count)

$ancestry = @{}
foreach ($g in $captured.Values) {
    # 거슬러 올라가서 root parent 찾기
    $chain = @($g.Name + "(PID " + $g.ProcessId + ")")
    $cur = $g
    $depth = 0
    while ($cur -and $depth -lt 6) {
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($cur.ParentProcessId)" -ErrorAction SilentlyContinue
        if (-not $parent) { break }
        $cmdShort = if ($parent.CommandLine) { $parent.CommandLine.Substring(0,[Math]::Min(100,$parent.CommandLine.Length)) } else { '' }
        $chain += ("$($parent.Name) | $cmdShort")
        $cur = $parent
        $depth++
        if ($parent.Name -in @('explorer.exe','services.exe','wininit.exe','svchost.exe','System')) { break }
    }
    $rootKey = $chain[-1]
    if (-not $ancestry.ContainsKey($rootKey)) {
        $ancestry[$rootKey] = @{ count = 0; sample_chain = $chain }
    }
    $ancestry[$rootKey].count++
}

Write-Host "=== Root ancestor of git.exe spawns ==="
$ancestry.GetEnumerator() | Sort-Object { $_.Value.count } -Descending | ForEach-Object {
    Write-Host ("`n  [{0}x]  ROOT: {1}" -f $_.Value.count, $_.Key)
    foreach ($step in $_.Value.sample_chain) {
        Write-Host ("    -> {0}" -f $step.Substring(0,[Math]::Min(120,$step.Length)))
    }
}

Write-Host ""
Write-Host "=== Antigravity processes currently running ==="
Get-CimInstance Win32_Process -Filter "Name='Antigravity.exe'" | Select-Object ProcessId, ParentProcessId, @{N='cmd';E={if($_.CommandLine){$_.CommandLine.Substring(0,[Math]::Min(120,$_.CommandLine.Length))}else{''}}} | Format-Table -AutoSize -Wrap

Write-Host ""
Write-Host "=== Workspaces opened in Antigravity ==="
$agStorage = "$env:APPDATA\Antigravity\User\workspaceStorage"
if (Test-Path $agStorage) {
    Get-ChildItem $agStorage | ForEach-Object {
        $ws = Join-Path $_.FullName "workspace.json"
        if (Test-Path $ws) {
            try {
                $j = Get-Content $ws -Raw | ConvertFrom-Json
                Write-Host ("  {0}" -f $j.folder)
            } catch {}
        }
    }
}
