# RPA 디버그 런처 - 에러를 파일로 캡처
$py      = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe"
$base    = "Q:\Claudework\bridge base"
$log     = "$base\logs\debug_launch.log"
Set-Location $base

"=== DEBUG LAUNCH $(Get-Date) ===" | Out-File $log -Encoding UTF8

# account1, 2, 3 순서로 generate(브라우저 없음) 실행해서 에러 확인
foreach ($acct in @("account1","account2","account3")) {
    "--- $acct ---" | Out-File $log -Append -Encoding UTF8
    $r = & $py "craigslist_auto_rpa.py" "--account" $acct "--generate" "--limit" "1" 2>&1
    $r | Out-File $log -Append -Encoding UTF8
    "exit=$LASTEXITCODE" | Out-File $log -Append -Encoding UTF8
}

# headless 실제 실행 시도 (account1, limit=1) - ChromeDriver 단계까지 에러 확인
"--- HEADLESS account1 limit=1 ---" | Out-File $log -Append -Encoding UTF8
$r2 = & $py "craigslist_auto_rpa.py" "--account" "account1" "--limit" "1" "--headless" 2>&1
$r2 | Out-File $log -Append -Encoding UTF8
"exit=$LASTEXITCODE" | Out-File $log -Append -Encoding UTF8

Write-Host "Done -> $log"
