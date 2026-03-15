$logdir = "Q:\Claudework\bridge base\logs"

# lock 파일 + 잔여 flag 파일 정리
$targets = @(".rpa_account1.lock", ".rpa_account2.lock", ".rpa_account3.lock", ".rpa_account4.lock",
             ".rpa_default.lock", ".overlay_restore.flag", ".overlay_hwnd.txt")

foreach ($t in $targets) {
    $p = [System.IO.Path]::Combine($logdir, $t)
    if ([System.IO.File]::Exists($p)) {
        [System.IO.File]::Delete($p)
        Write-Host ("삭제: " + $t)
    }
}

Write-Host ""
Write-Host "=== 남은 파일 ==="
$remaining = [System.IO.Directory]::GetFiles($logdir)
foreach ($f in $remaining) {
    Write-Host ("  " + [System.IO.Path]::GetFileName($f))
}
Write-Host "완료"
