$src = "Q:\Claudework\bridge base"
$dst = "K:\BPAver2"
[System.IO.Directory]::CreateDirectory($dst) | Out-Null
$files = "rpa_overlay.py","launcher.pyw","craigslist_auto_rpa.py","account1.env","account2.env","account3.env","account4.env","requirements_rpa.txt"
foreach ($f in $files) {
    $s = [System.IO.Path]::Combine($src, $f)
    $d = [System.IO.Path]::Combine($dst, $f)
    if ([System.IO.File]::Exists($s)) {
        [System.IO.File]::Copy($s, $d, $true)
        Write-Host ("OK: " + $f)
    } else {
        Write-Host ("SKIP: " + $f)
    }
}
Write-Host ""
Write-Host "=== K:\BPAver2 백업 목록 ==="
[System.IO.Directory]::GetFiles($dst) | ForEach-Object {
    $fi = [System.IO.FileInfo]$_
    Write-Host ($fi.Name + "  [" + $fi.Length + " bytes]")
}
Write-Host "BACKUP_DONE"
