# Find all places that call start_craig.vbs or reference it

Write-Host "--- Desktop shortcuts ---"
Get-ChildItem "$env:USERPROFILE\Desktop" -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.Extension -eq ".lnk") {
        $shell = New-Object -ComObject WScript.Shell
        $sc = $shell.CreateShortcut($_.FullName)
        if ($sc.TargetPath -match "wscript|craig" -or $sc.Arguments -match "craig") {
            Write-Host "[$($_.Name)] Target=$($sc.TargetPath) Args=$($sc.Arguments)"
        }
    }
    if ($_.Name -match "craig") {
        Write-Host "DESKTOP FILE: $($_.Name)"
    }
}

Write-Host ""
Write-Host "--- All scheduled tasks referencing start_craig ---"
Get-ScheduledTask -ErrorAction SilentlyContinue | ForEach-Object {
    $tn = $_.TaskName
    $_.Actions | ForEach-Object {
        if ($_.Arguments -match "craig" -or $_.Execute -match "craig") {
            Write-Host "Task: $tn | Execute: $($_.Execute) | Args: $($_.Arguments)"
        }
    }
}

Write-Host ""
Write-Host "--- HKCU/HKLM Run with craig ---"
@("HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
  "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run") | ForEach-Object {
    $k = Get-ItemProperty $_ -ErrorAction SilentlyContinue
    if ($k) {
        $k.PSObject.Properties | Where-Object { $_.Name -notmatch "^PS" -and $_.Value -match "craig" } | ForEach-Object {
            Write-Host "$($_.Name) = $($_.Value)"
        }
    }
}

Write-Host ""
Write-Host "--- start_craig.vbs in bridge base ---"
Get-Content "Q:\Claudework\bridge base\start_craig.vbs" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "--- Any script calling start_craig ---"
Get-ChildItem "Q:\" -Recurse -Include "*.bat","*.cmd","*.ps1","*.vbs","*.ahk" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "_BACKUP|backups|__pycache__|tools\\check|tools\\find|tools\\grep|tools\\check_craig" } |
    ForEach-Object {
        $content = Get-Content $_.FullName -ErrorAction SilentlyContinue -Raw
        if ($content -match "start_craig") {
            Write-Host "CALLER: $($_.FullName)"
            ($content -split "`n" | Select-String "start_craig") | ForEach-Object { Write-Host "  $_" }
        }
    }
