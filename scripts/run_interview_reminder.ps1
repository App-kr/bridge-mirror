# Bridge Interview Reminder Runner — Windows Task Scheduler용
# 10분 간격 실행, 인터뷰 30분 전 자동 리마인더 발송
# 보안: .env 파일에서 SMTP 크리덴셜 로드

$ProjectRoot = "Q:\Claudework\bridge base"

Set-Location $ProjectRoot

try {
    & python tools/interview_reminder.py 2>&1 | Out-Null
} catch {
    $errTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path "$ProjectRoot\logs\interview_reminder.log" -Value "[$errTime] RUNNER ERROR: $_" -Encoding UTF8
}
