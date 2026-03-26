$all = Get-ScheduledTask | ForEach-Object {
    $t = $_
    $cmd = ($t.Actions | ForEach-Object { $_.Execute }) -join ";"
    [PSCustomObject]@{
        Name   = $t.TaskName
        Path   = $t.TaskPath
        Hidden = $t.Settings.Hidden
        Cmd    = $cmd
    }
} | Where-Object { $_.Cmd -match "powershell|python|wscript|bat" }

Write-Host "=== All startup tasks ==="
$all | Format-Table Name, Path, Hidden -AutoSize

$notHidden = $all | Where-Object { $_.Hidden -eq $false -or $_.Hidden -eq $null }
if ($notHidden) {
    Write-Host "=== Still NOT hidden (may show window) ===" -ForegroundColor Red
    $notHidden | Format-Table Name, Path, Hidden -AutoSize
} else {
    Write-Host "=== All tasks are now hidden ===" -ForegroundColor Green
}
