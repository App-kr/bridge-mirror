$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== PowerShell.exe spawn full ancestry (20s) ==="
$captured = @{}
$end = (Get-Date).AddSeconds(20)
while ((Get-Date) -lt $end) {
    Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" | ForEach-Object {
        if (-not $captured.ContainsKey($_.ProcessId)) {
            $captured[$_.ProcessId] = $_
        }
    }
    Start-Sleep -Milliseconds 200
}

Write-Host ("Captured {0} unique powershell.exe in 20s`n" -f $captured.Count)

# 각각의 부모 + 명령어
$parents = @{}
foreach ($p in $captured.Values) {
    $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($p.ParentProcessId)" -ErrorAction SilentlyContinue
    $pname = if ($parent) { $parent.Name } else { 'GONE' }
    $pcmd = if ($parent -and $parent.CommandLine) {
        $parent.CommandLine.Substring(0,[Math]::Min(150,$parent.CommandLine.Length))
    } else { '' }
    $key = $pname
    if (-not $parents.ContainsKey($key)) {
        $parents[$key] = @{ count = 0; samples = @() }
    }
    $parents[$key].count++
    if ($parents[$key].samples.Count -lt 3) {
        $myCmd = if ($p.CommandLine) { $p.CommandLine.Substring(0,[Math]::Min(120,$p.CommandLine.Length)) } else { '' }
        $parents[$key].samples += @{
            mycmd = $myCmd
            parentcmd = $pcmd
        }
    }
}

Write-Host "=== Top spawners ==="
$parents.GetEnumerator() | Sort-Object { $_.Value.count } -Descending | ForEach-Object {
    Write-Host ""
    Write-Host ("  [{0}x]  parent: {1}" -f $_.Value.count, $_.Key)
    foreach ($s in $_.Value.samples) {
        Write-Host ("    PARENT_CMD: {0}" -f $s.parentcmd)
        Write-Host ("    POWERSHELL: {0}" -f $s.mycmd)
    }
}

Write-Host ""
Write-Host "=== tg_approval_daemon currently running? ==="
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*tg_approval_daemon*' } |
    Select ProcessId, @{N='age_min';E={[math]::Round(((Get-Date)-$_.CreationDate).TotalMinutes,1)}}, ExecutablePath |
    Format-List
