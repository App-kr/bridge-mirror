# Find tasks that use python.exe (console-attached) instead of pythonw.exe (no console)
$ErrorActionPreference = 'SilentlyContinue'

Write-Host "=== Tasks using python.exe (console window appears) ==="
$hits = @()
Get-ScheduledTask | Where-Object {
    $_.TaskPath -notlike '\Microsoft\*' -and $_.State -ne 'Disabled'
} | ForEach-Object {
    $t = $_
    foreach ($a in $t.Actions) {
        # python.exe (NOT pythonw.exe) is the culprit
        if ($a.Execute -match '\\python\.exe(\"|$)' -or $a.Execute -match '/python\.exe$') {
            $hits += [PSCustomObject]@{
                Path = $t.TaskPath
                Name = $t.TaskName
                Exec = $a.Execute
                Args = $a.Arguments
            }
        }
    }
}
$hits | Format-Table -AutoSize -Wrap
Write-Host ("Total: {0}" -f $hits.Count)

Write-Host "`n=== Tasks using node.exe directly (also console) ==="
Get-ScheduledTask | Where-Object {
    $_.TaskPath -notlike '\Microsoft\*' -and $_.State -ne 'Disabled'
} | ForEach-Object {
    $t = $_
    foreach ($a in $t.Actions) {
        if ($a.Execute -match 'node\.exe$') {
            [PSCustomObject]@{
                Name = ($t.TaskPath + $t.TaskName)
                Exec = $a.Execute
                Args = $a.Arguments
            }
        }
    }
} | Format-Table -AutoSize -Wrap
