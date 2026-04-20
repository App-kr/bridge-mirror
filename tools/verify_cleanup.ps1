Get-ScheduledTask -TaskName 'BRIDGE_GDrive_Backup','BRIDGE_GDrive_Backup_Frequent' | ForEach-Object {
    Write-Host ""
    Write-Host ("Task: " + $_.TaskName)
    foreach ($a in $_.Actions) {
        Write-Host ("  Exec=" + $a.Execute)
        Write-Host ("  Args=" + $a.Arguments)
    }
}
Write-Host ""
Write-Host "=== on_startup.ps1 syntax check ==="
$err = $null
try {
    [System.Management.Automation.PSParser]::Tokenize((Get-Content "Q:\Claudework\on_startup.ps1" -Raw), [ref]$err) | Out-Null
    if ($err -and $err.Count -gt 0) {
        Write-Host "ERRORS: $($err.Count)"
        $err | Format-List
    } else {
        Write-Host "SYNTAX OK"
    }
} catch {
    Write-Host "Parse failed: $_"
}

Write-Host ""
Write-Host "=== Startup folder ==="
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup" -Force | Select Name, Length, LastWriteTime | Format-Table -AutoSize
