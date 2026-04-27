# 2026-04-27 - Identify tasks that pop up cmd/PowerShell windows (focus steal)
$ErrorActionPreference = 'SilentlyContinue'

Write-Host "=== A) Tasks calling cmd.exe directly (cmd window appears) ==="
Get-ScheduledTask | Where-Object {
    $_.TaskPath -notlike '\Microsoft\*' -and $_.State -ne 'Disabled'
} | ForEach-Object {
    $t = $_
    foreach ($a in $t.Actions) {
        if ($a.Execute -match 'cmd\.exe$') {
            [PSCustomObject]@{
                Path = $t.TaskPath
                Name = $t.TaskName
                Exec = $a.Execute
                Args = $a.Arguments
            }
        }
    }
} | Format-Table -AutoSize -Wrap

Write-Host "`n=== B) Tasks calling powershell.exe WITHOUT -WindowStyle Hidden ==="
Get-ScheduledTask | Where-Object {
    $_.TaskPath -notlike '\Microsoft\*' -and $_.State -ne 'Disabled'
} | ForEach-Object {
    $t = $_
    foreach ($a in $t.Actions) {
        if (($a.Execute -match 'powershell(\.exe)?$' -or $a.Execute -match 'pwsh(\.exe)?$') -and
            ($a.Arguments -notmatch 'WindowStyle\s+Hidden' -and $a.Arguments -notmatch '-w\s+hidden')) {
            [PSCustomObject]@{
                Path = $t.TaskPath
                Name = $t.TaskName
                Args = $a.Arguments
            }
        }
    }
} | Format-Table -AutoSize -Wrap

Write-Host "`n=== C) Tasks calling .bat directly (cmd hosts the bat) ==="
Get-ScheduledTask | Where-Object {
    $_.TaskPath -notlike '\Microsoft\*' -and $_.State -ne 'Disabled'
} | ForEach-Object {
    $t = $_
    foreach ($a in $t.Actions) {
        if ($a.Execute -match '\.bat$' -or $a.Execute -match '\.cmd$') {
            [PSCustomObject]@{
                Path = $t.TaskPath
                Name = $t.TaskName
                Exec = $a.Execute
                Args = $a.Arguments
            }
        }
    }
} | Format-Table -AutoSize -Wrap

Write-Host "`n=== D) Tasks running while user is logged on (visible candidates) ==="
# Settings.RunOnlyIfLoggedOn = $true means it can show windows
Get-ScheduledTask | Where-Object {
    $_.TaskPath -notlike '\Microsoft\*' -and $_.State -ne 'Disabled'
} | ForEach-Object {
    $info = $_.Settings
    if ($info.RunOnlyIfLoggedOn -or $info.Hidden -ne $true) {
        # Look for direct cmd/bat
        foreach ($a in $_.Actions) {
            if ($a.Execute -match 'cmd\.exe|\.bat$|\.cmd$' -or
                ($a.Execute -match 'powershell' -and $a.Arguments -notmatch 'Hidden')) {
                [PSCustomObject]@{
                    Name = $_.TaskName
                    Hidden = $info.Hidden
                    LoggedOn = $info.RunOnlyIfLoggedOn
                    Exec = $a.Execute
                }
                break
            }
        }
    }
} | Format-Table -AutoSize -Wrap

Write-Host "`n=== E) Recently fired tasks (last 6 hours - smoking gun) ==="
$cutoff = (Get-Date).AddHours(-6)
Get-ScheduledTask | Where-Object { $_.TaskPath -notlike '\Microsoft\*' } | ForEach-Object {
    $info = $_ | Get-ScheduledTaskInfo
    if ($info.LastRunTime -gt $cutoff) {
        [PSCustomObject]@{
            Name    = ($_.TaskPath + $_.TaskName)
            LastRun = $info.LastRunTime
            Result  = $info.LastTaskResult
            Exec    = ($_.Actions | Select-Object -First 1).Execute
        }
    }
} | Sort-Object LastRun -Descending | Select-Object -First 20 | Format-Table -AutoSize -Wrap
