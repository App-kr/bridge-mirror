$ErrorActionPreference = 'SilentlyContinue'
Write-Host "=== 1) Startup lnk inspection ==="
$sh = New-Object -ComObject WScript.Shell
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup" -Force | ForEach-Object {
    if ($_.Extension -in '.lnk','.bak') {
        $p = $_.FullName
        try {
            $lnk = $sh.CreateShortcut($p)
            Write-Host ("FILE : {0}" -f $p)
            Write-Host ("  TARGET: {0}" -f $lnk.TargetPath)
            Write-Host ("  ARGS  : {0}" -f $lnk.Arguments)
            Write-Host ("  WDIR  : {0}" -f $lnk.WorkingDirectory)
        } catch { Write-Host ("  (not a shortcut)") }
    }
}

Write-Host "`n=== 2) Non-MS Scheduled Tasks ==="
Get-ScheduledTask | Where-Object { $_.TaskPath -notlike '\Microsoft\*' -and $_.State -ne 'Disabled' } |
    Select-Object TaskName, TaskPath, State | Format-Table -AutoSize

Write-Host "`n=== 3) Task actions detail ==="
Get-ScheduledTask | Where-Object { $_.TaskPath -notlike '\Microsoft\*' } | ForEach-Object {
    $n = $_.TaskName; $p = $_.TaskPath
    foreach ($a in $_.Actions) {
        Write-Host ("[{0}{1}] exec={2} args={3}" -f $p,$n,$a.Execute,$a.Arguments)
    }
}

Write-Host "`n=== 4) WMI Subscriptions ==="
Get-WmiObject -Namespace root\subscription -Class __EventFilter | Select Name, Query | Format-List
Get-WmiObject -Namespace root\subscription -Class __EventConsumer | Select Name, CommandLineTemplate | Format-List

Write-Host "`n=== 5) Services (Auto, non-MS) ==="
Get-CimInstance Win32_Service | Where-Object { $_.StartMode -eq 'Auto' -and $_.PathName -notlike '*System32*' -and $_.PathName -notlike '*Program Files*Windows*' } |
    Select-Object Name, DisplayName, PathName, State | Format-List

Write-Host "`n=== 6) HWP file association ==="
cmd /c "assoc .hwp" 2>$null
cmd /c "ftype HWP.Document" 2>$null
cmd /c "ftype HwpApp.Document" 2>$null

Write-Host "`n=== 7) HWP auto-open candidates in Documents / Desktop / Downloads ==="
foreach ($dir in @("$env:USERPROFILE\Desktop","$env:USERPROFILE\Documents","$env:USERPROFILE\Downloads")) {
    Get-ChildItem $dir -Filter *.hwp -Force -ErrorAction SilentlyContinue | Select FullName, Length, LastWriteTime
}

Write-Host "`n=== 8) Explorer Shell Folders Startup override ==="
Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders' | Format-List Startup, 'Common Startup'
