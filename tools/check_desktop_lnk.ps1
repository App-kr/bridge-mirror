# Check desktop shortcuts for wscript calls
$Desktop = [Environment]::GetFolderPath("Desktop")
Write-Host "=== Desktop LNK files ==="
Write-Host "Desktop path: $Desktop"

$links = Get-ChildItem $Desktop -Filter "*.lnk" -ErrorAction SilentlyContinue
foreach ($link in $links) {
    Write-Host ""
    Write-Host "LNK: $($link.Name)"
    try {
        $shell = New-Object -ComObject WScript.Shell
        $sc = $shell.CreateShortcut($link.FullName)
        Write-Host "  Target: $($sc.TargetPath)"
        Write-Host "  Args:   $($sc.Arguments)"
        Write-Host "  WorkDir:$($sc.WorkingDirectory)"
        if ($sc.TargetPath -like "*wscript*") {
            Write-Host "  *** CALLS WSCRIPT ***"
            if ($sc.Arguments -notlike '"*"') {
                Write-Host "  *** UNQUOTED ARGS? ***"
            }
        }
    } catch {}
}

# Also check for any Q:\Claudework\bridge related items
Write-Host ""
Write-Host "=== All LNK files that reference bridge ==="
Get-ChildItem $Desktop -Filter "*.lnk" -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $sh = New-Object -ComObject WScript.Shell
        $sc = $sh.CreateShortcut($_.FullName)
        if ($sc.TargetPath -like "*bridge*" -or $sc.Arguments -like "*bridge*") {
            Write-Host "  LNK: $($_.Name)"
            Write-Host "    Target: $($sc.TargetPath)"
            Write-Host "    Args:   $($sc.Arguments)"
        }
    } catch {}
}

# Check for wscript in HKCU Run more carefully
Write-Host ""
Write-Host "=== HKCU Run entries full details ==="
$run = Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue
$run.PSObject.Properties | Where-Object { $_.MemberType -eq "NoteProperty" -and $_.Name -notmatch "^PS" } | ForEach-Object {
    Write-Host "$($_.Name): $($_.Value)"
    if ($_.Value -like "*wscript*") {
        Write-Host "  *** WSCRIPT IN RUN KEY ***"
    }
}
