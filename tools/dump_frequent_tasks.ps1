# Dump frequent tasks (5/10/15/30-min interval) - prime suspects for cmd flicker
$ErrorActionPreference = 'SilentlyContinue'

Write-Host "=== Frequent BRIDGE/Bridge tasks (interval <= 30min) ==="
Get-ScheduledTask | Where-Object {
    $_.TaskPath -notlike '\Microsoft\*' -and
    ($_.TaskName -match 'BRIDGE|Bridge|Claude|RPA|Audio|Headset|GDrive|DB|Render')
} | ForEach-Object {
    $t = $_
    $fastest = $null
    foreach ($tr in $t.Triggers) {
        $rep = $tr.Repetition
        if ($rep -and $rep.Interval) {
            # PT5M -> 5 min
            $iv = $rep.Interval
            if ($iv -match 'PT(\d+)M') {
                $mins = [int]$Matches[1]
                if (-not $fastest -or $mins -lt $fastest) { $fastest = $mins }
            }
        }
    }
    if ($fastest -and $fastest -le 30) {
        foreach ($a in $t.Actions) {
            [PSCustomObject]@{
                Mins = $fastest
                Name = ($t.TaskPath + $t.TaskName)
                Exec = $a.Execute
                Args = if ($a.Arguments) { $a.Arguments.Substring(0,[Math]::Min(160,$a.Arguments.Length)) } else { '' }
            }
        }
    }
} | Sort-Object Mins | Format-Table -AutoSize -Wrap

Write-Host "`n=== Find subprocess.run/Popen WITHOUT CREATE_NO_WINDOW in BRIDGE auto-scripts ==="
$scripts = @(
    'Q:\Claudework\bridge base\.hooks\auto_backup.py',
    'Q:\Claudework\bridge base\tools\db_drive_backup.py',
    'Q:\Claudework\bridge base\tools\auto_security_patch.py',
    'Q:\Claudework\bridge base\tools\behavior_baseline.py',
    'Q:\Claudework\bridge base\tools\ioc_watcher.py',
    'Q:\Claudework\bridge base\tools\threat_feed.py',
    'Q:\Claudework\bridge base\tools\db_sync_daemon.py',
    'Q:\Claudework\bridge base\tools\render_monitor.py',
    'Q:\Claudework\bridge base\tools\email_autoresponder.py',
    'Q:\Claudework\bridge base\tools\email_reporter.py',
    'Q:\Claudework\bridge base\tools\render_keepalive.py'
)
foreach ($s in $scripts) {
    if (Test-Path $s) {
        $matches = Select-String -Path $s -Pattern 'subprocess\.(run|Popen|call|check_call|check_output)' -SimpleMatch
        $hasNoWindow = Select-String -Path $s -Pattern 'CREATE_NO_WINDOW' -SimpleMatch -Quiet
        if ($matches -and -not $hasNoWindow) {
            Write-Host ("[VULN] {0} - {1} subprocess calls, NO CREATE_NO_WINDOW" -f $s, $matches.Count)
            $matches | Select-Object -First 2 | ForEach-Object { Write-Host ("    L{0}: {1}" -f $_.LineNumber, $_.Line.Trim().Substring(0,[Math]::Min(100,$_.Line.Trim().Length))) }
        } elseif ($matches) {
            Write-Host ("[OK]   {0} - {1} subprocess calls, has CREATE_NO_WINDOW" -f $s, $matches.Count)
        }
    } else {
        Write-Host ("[N/A]  {0}" -f $s)
    }
}
