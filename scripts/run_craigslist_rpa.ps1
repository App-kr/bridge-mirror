# Bridge Craigslist RPA Runner — Windows Task Scheduler용
# 경로 공백 문제 해결을 위해 PowerShell 래퍼 사용
# 보안: .env 파일에서 크리덴셜 로드, 하드코딩 없음

$ProjectRoot = "Q:\Claudework\bridge base"
$LogDir = "$ProjectRoot\logs"
$LogFile = "$LogDir\scheduler.log"
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# 로그 디렉토리 확인
if (-not (Test-Path $LogDir)) {
    New-Item -Path $LogDir -ItemType Directory -Force | Out-Null
}

Add-Content -Path $LogFile -Value "[$Timestamp] RPA START" -Encoding UTF8

Set-Location $ProjectRoot

try {
    $result = & python tools/craigslist_auto_rpa.py --headless --limit 10 2>&1
    $exitCode = $LASTEXITCODE
    $endTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    if ($exitCode -eq 0) {
        Add-Content -Path $LogFile -Value "[$endTime] RPA SUCCESS (exit=$exitCode)" -Encoding UTF8
    } else {
        Add-Content -Path $LogFile -Value "[$endTime] RPA FAILED (exit=$exitCode): $result" -Encoding UTF8
    }
} catch {
    $errTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "[$errTime] RPA ERROR: $_" -Encoding UTF8
}
