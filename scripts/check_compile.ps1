$py = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe"
$files = @("rpa_overlay.py", "craigslist_auto_rpa.py")
foreach ($f in $files) {
    $r = & $py -m py_compile "Q:\Claudework\bridge base\$f" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK: $f"
    } else {
        Write-Host "FAIL: $f"
        $r | Out-String | Write-Host
    }
}
