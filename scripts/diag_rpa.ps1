# RPA 진단 스크립트 — 에러를 파일로 캡처
$py      = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe"
$base    = "Q:\Claudework\bridge base"
$logfile = "$base\logs\rpa_diag.log"
Set-Location $base

# 1. account env 키 확인 (값 노출 없이)
"=== ENV KEYS ===" | Out-File $logfile -Encoding UTF8
foreach ($n in @("account1","account2","account3")) {
    $f = "$base\$n.env"
    if (Test-Path $f) {
        "[$n.env]" | Out-File $logfile -Append -Encoding UTF8
        Get-Content $f | ForEach-Object {
            ($_ -split "=")[0]
        } | Out-File $logfile -Append -Encoding UTF8
    }
}

# 2. integrity hash 파일 확인
"=== INTEGRITY ===" | Out-File $logfile -Append -Encoding UTF8
$hf = "$base\logs\.file_hashes.json"
if (Test-Path $hf) {
    "hash file exists" | Out-File $logfile -Append -Encoding UTF8
} else {
    "hash file MISSING - will auto-init on first run" | Out-File $logfile -Append -Encoding UTF8
}

# 3. account1 으로 generate (브라우저 없이) — 에러 캡처
"=== GENERATE TEST (account1, limit=1) ===" | Out-File $logfile -Append -Encoding UTF8
$result = & $py "craigslist_auto_rpa.py" "--account" "account1" "--generate" "--limit" "1" 2>&1
$result | Out-File $logfile -Append -Encoding UTF8
"exit code: $LASTEXITCODE" | Out-File $logfile -Append -Encoding UTF8

# 4. account1 으로 dry-run — 에러 캡처
"=== DRY-RUN TEST (account1, limit=1) ===" | Out-File $logfile -Append -Encoding UTF8
$result2 = & $py "craigslist_auto_rpa.py" "--account" "account1" "--dry-run" "--limit" "1" 2>&1
$result2 | Out-File $logfile -Append -Encoding UTF8
"exit code: $LASTEXITCODE" | Out-File $logfile -Append -Encoding UTF8

Write-Host "Done. Log: $logfile"
