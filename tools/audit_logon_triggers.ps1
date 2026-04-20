$ErrorActionPreference = 'SilentlyContinue'
Write-Host "=== Logon / Boot-triggered tasks (non-MS) ==="
Get-ScheduledTask | Where-Object {
    $_.TaskPath -notlike '\Microsoft\*' -and $_.State -ne 'Disabled'
} | ForEach-Object {
    $t = $_
    $triggers = @()
    foreach ($tr in $t.Triggers) {
        $cn = $tr.CimClass.CimClassName
        if ($cn -eq 'MSFT_TaskLogonTrigger' -or $cn -eq 'MSFT_TaskBootTrigger') {
            $triggers += $cn
        }
    }
    if ($triggers.Count -gt 0) {
        foreach ($a in $t.Actions) {
            [PSCustomObject]@{
                Path    = $t.TaskPath
                Name    = $t.TaskName
                Trigger = ($triggers -join ',')
                Exec    = $a.Execute
                Args    = $a.Arguments
            }
        }
    }
} | Format-Table -AutoSize -Wrap

Write-Host "`n=== Tasks missing -WindowStyle Hidden (visible PS candidates) ==="
Get-ScheduledTask | Where-Object {
    $_.TaskPath -notlike '\Microsoft\*' -and $_.State -ne 'Disabled'
} | ForEach-Object {
    $t = $_
    foreach ($a in $t.Actions) {
        if ($a.Execute -like '*powershell*' -or $a.Execute -like '*pwsh*' -or $a.Execute -like '*cmd.exe*') {
            $isHidden = ($a.Arguments -match 'WindowStyle\s+Hidden' -or $a.Arguments -match '-w\s+hidden')
            if (-not $isHidden) {
                [PSCustomObject]@{
                    Name = ($t.TaskPath + $t.TaskName)
                    Exec = $a.Execute
                    Args = $a.Arguments
                }
            }
        }
    }
} | Format-Table -AutoSize -Wrap

Write-Host "`n=== ClaudeworkAutoRestore triggers & script content check ==="
Get-ScheduledTask -TaskName "ClaudeworkAutoRestore" | Select-Object -ExpandProperty Triggers | Format-List *
if (Test-Path "Q:\Claudework\on_startup.ps1") {
    Write-Host "--- Q:\Claudework\on_startup.ps1 (first 80 lines) ---"
    Get-Content "Q:\Claudework\on_startup.ps1" -TotalCount 80
}
