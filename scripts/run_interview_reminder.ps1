# Bridge Interview Reminder Runner — Windows Task Scheduler용
# 10분 간격 실행, 인터뷰 30분 전 자동 리마인더 발송
# 보안: .env 파일에서 SMTP 크리덴셜 로드

$ProjectRoot = "Q:\Claudework\bridge base"
$PythonExe  = "Q:\Phtyon 3\python.exe"
$LogFile    = "$ProjectRoot\logs\interview_reminder.log"

function Write-RLog($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "[$ts] $msg" -Encoding UTF8
}

if (-not (Test-Path $PythonExe)) {
    Write-RLog "SKIP: python not found at $PythonExe"
    exit 0
}

try {
    # -WindowStyle Hidden: 콘솔 창 없이 백그라운드 실행
    $p = Start-Process `
        -FilePath $PythonExe `
        -ArgumentList "-X utf8 `"$ProjectRoot\tools\interview_reminder.py`"" `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden `
        -PassThru `
        -ErrorAction Stop
    $p.WaitForExit(30000)   # 최대 30초 대기
} catch {
    Write-RLog "RUNNER ERROR: $_"
}
