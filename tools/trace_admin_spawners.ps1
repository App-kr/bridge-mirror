$ErrorActionPreference = 'SilentlyContinue'

Write-Host "=== A) RunLevel=HIGHEST tasks (admin elevation -> visible UAC/cmd window) ==="
Get-ScheduledTask | Where-Object {
    $_.TaskPath -notlike '\Microsoft\*' -and $_.State -ne 'Disabled'
} | ForEach-Object {
    $t = $_
    $principal = $t.Principal
    if ($principal.RunLevel -eq 'Highest') {
        foreach ($a in $t.Actions) {
            [PSCustomObject]@{
                Name = ($t.TaskPath + $t.TaskName)
                User = $principal.UserId
                Hidden = $t.Settings.Hidden
                Exec = $a.Execute
                Args = if ($a.Arguments) { $a.Arguments.Substring(0,[Math]::Min(100,$a.Arguments.Length)) } else { '' }
            }
        }
    }
} | Format-Table -AutoSize -Wrap

Write-Host "`n=== B) Tasks with interval <= 5min (every-few-second culprits) ==="
Get-ScheduledTask | Where-Object {
    $_.TaskPath -notlike '\Microsoft\*' -and $_.State -ne 'Disabled'
} | ForEach-Object {
    $t = $_
    foreach ($tr in $t.Triggers) {
        $rep = $tr.Repetition
        if ($rep -and $rep.Interval) {
            $iv = $rep.Interval
            if ($iv -match 'PT(\d+)M' -and [int]$Matches[1] -le 5) {
                foreach ($a in $t.Actions) {
                    [PSCustomObject]@{
                        Mins = [int]$Matches[1]
                        Name = ($t.TaskPath + $t.TaskName)
                        Hidden = $t.Settings.Hidden
                        Exec = $a.Execute
                        Args = if ($a.Arguments) { $a.Arguments.Substring(0,[Math]::Min(100,$a.Arguments.Length)) } else { '' }
                    }
                    break
                }
                break
            }
            if ($iv -match 'PT(\d+)S') {
                foreach ($a in $t.Actions) {
                    [PSCustomObject]@{
                        Mins = ('${0}s' -f $Matches[1])
                        Name = ($t.TaskPath + $t.TaskName)
                        Hidden = $t.Settings.Hidden
                        Exec = $a.Execute
                        Args = if ($a.Arguments) { $a.Arguments.Substring(0,[Math]::Min(100,$a.Arguments.Length)) } else { '' }
                    }
                    break
                }
            }
        }
    }
} | Sort-Object Mins | Format-Table -AutoSize -Wrap

Write-Host "`n=== C) Watch active cmd/powershell spawning over 15 seconds ==="
$snap1 = @{}
Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(cmd|powershell|conhost|pwsh)\.exe$' } | ForEach-Object {
    $snap1[$_.ProcessId] = $_.Name
}
Start-Sleep -Seconds 15
$snap2 = @{}
Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(cmd|powershell|conhost|pwsh)\.exe$' } | ForEach-Object {
    $snap2[$_.ProcessId] = $_.Name
}
$newProcs = $snap2.Keys | Where-Object { -not $snap1.ContainsKey($_) }
Write-Host "New cmd/powershell/conhost spawned in 15s: $($newProcs.Count)"
foreach ($pid in $newProcs) {
    $p = Get-CimInstance Win32_Process -Filter "ProcessId=$pid"
    if ($p) {
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($p.ParentProcessId)"
        Write-Host ("  NEW PID={0} {1} | PARENT={2} ({3}) | CMD={4}" -f
            $p.ProcessId, $p.Name, $p.ParentProcessId, $parent.Name,
            (if ($p.CommandLine) { $p.CommandLine.Substring(0,[Math]::Min(100,$p.CommandLine.Length)) } else { '' }))
    }
}
