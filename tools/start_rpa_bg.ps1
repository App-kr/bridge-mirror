# BRIDGE Craigslist RPA — 백그라운드 독립 프로세스 실행
# CMD/PowerShell 창 종료 후에도 계속 실행됨

$rpaPythonPath = "Q:\Claudework\bridge base\craigslist_auto_rpa.py"
$logPath       = "Q:\Claudework\bridge base\logs\craigslist_rpa.log"
$errPath       = "Q:\Claudework\bridge base\logs\craigslist_rpa.err"
$pidFile       = "Q:\Claudework\bridge base\craigslist_rpa.pid"
$pythonw       = "C:\Python314\pythonw.exe"

# 로그 디렉토리 생성
New-Item -ItemType Directory -Path (Split-Path $logPath) -Force | Out-Null

# 이미 실행 중이면 종료
if (Test-Path $pidFile) {
    $oldPid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($oldPid) {
        Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
        Write-Host "이전 프로세스 종료 (PID $oldPid)" -ForegroundColor Yellow
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

# pythonw.exe 확인 (없으면 python.exe 사용)
if (-not (Test-Path $pythonw)) {
    $pythonw = (Get-Command python.exe -ErrorAction SilentlyContinue)?.Source
    if (-not $pythonw) {
        Write-Host "Python을 찾을 수 없습니다." -ForegroundColor Red
        exit 1
    }
}

# 백그라운드 워커 실행 (창 없음, 독립 프로세스)
# -WindowStyle Hidden : 콘솔 창 없음
# -PassThru           : 프로세스 객체 반환
# Start-Process 로 실행한 프로세스는 이 PowerShell 세션과 무관하게 생존
$process = Start-Process -FilePath $pythonw `
    -ArgumentList "`"$rpaPythonPath`" --worker --limit=10 --no-relaunch" `
    -WorkingDirectory "Q:\Claudework\bridge base" `
    -WindowStyle Hidden `
    -PassThru

# PID 저장
$process.Id | Out-File -FilePath $pidFile -Encoding ASCII -Force

# 콘솔 모니터 실행 (이 창은 닫아도 Worker 무관)
$monitorPath = "Q:\Claudework\bridge base\rpa_console_monitor.py"
if (Test-Path $monitorPath) {
    Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/K python.exe -X utf8 `"$monitorPath`"" `
        -WorkingDirectory "Q:\Claudework\bridge base"
}

Write-Host "BRIDGE Craigslist RPA 백그라운드 시작" -ForegroundColor Green
Write-Host "PID    : $($process.Id)" -ForegroundColor Cyan
Write-Host "로그   : $logPath" -ForegroundColor Cyan
Write-Host "중단   : python Q:\Claudework\bridge base\tools\stop_rpa.ps1" -ForegroundColor Yellow
Write-Host "CMD 창 종료해도 계속 실행됨" -ForegroundColor Green
