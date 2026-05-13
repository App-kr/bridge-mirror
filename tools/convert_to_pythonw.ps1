$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$TASKS = @(
    'BRIDGE_AdminAccess_Monitor',
    'BRIDGE_CV_Pipeline',
    'BRIDGE_Daily_Backup',
    'MatjokdoHeart',
    'MatjokdoMain'
)

foreach ($name in $TASKS) {
    try {
        $task = Get-ScheduledTask -TaskName $name -ErrorAction Stop
        $newActions = @()
        foreach ($a in $task.Actions) {
            $newExe = $a.Execute -replace 'python\.exe', 'pythonw.exe' -replace 'python\.exe\"', 'pythonw.exe"'
            # 정확한 치환 (양쪽 슬래시)
            $newExe = $a.Execute
            if ($newExe -match 'python\.exe' -and $newExe -notmatch 'pythonw\.exe') {
                $newExe = $newExe -replace '\bpython\.exe', 'pythonw.exe'
                $newExe = $newExe -replace 'python\.exe(?!\w)', 'pythonw.exe'
            }
            $newAction = New-ScheduledTaskAction -Execute $newExe -Argument $a.Arguments
            $newActions += $newAction
            Write-Host ("$name : " + $a.Execute + " -> " + $newExe)
        }
        Set-ScheduledTask -TaskName $name -Action $newActions | Out-Null
        Write-Host "  OK updated"
    } catch {
        Write-Host ("  SKIP $name : " + $_.Exception.Message)
    }
}

Write-Host ""
Write-Host "=== Verify ==="
foreach ($name in $TASKS) {
    try {
        $task = Get-ScheduledTask -TaskName $name -ErrorAction Stop
        foreach ($a in $task.Actions) {
            $marker = if ($a.Execute -match 'pythonw\.exe') { 'OK' } else { 'STILL_PYTHON' }
            Write-Host ("[$marker] $name : " + $a.Execute)
        }
    } catch {}
}
