# BRIDGE Craigslist RPA — 백그라운드 독립 프로세스 실행
# CMD/PowerShell 창 종료 후에도 계속 실행됨

$rpaPythonPath = "Q:\Claudework\bridge base\craigslist_auto_rpa.py"
$logPath       = "Q:\Claudework\bridge base\logs\craigslist_rpa.log"
$errPath       = "Q:\Claudework\bridge base\logs\craigslist_rpa.err"
$pidFile       = "Q:\Claudework\bridge base\craigslist_rpa.pid"
$scriptPath    = "Q:\Claudework\bridge base\start_rpa_background.ps1"

# 로그 디렉토리 생성
New-Item -ItemType Directory -Path (Split-Path $logPath) -Force | Out-Null

# 이미 실행 중인 프로세스 종료
if (Test-Path $pidFile) {
    $oldPid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($oldPid) {
        Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
        Write-Host "이전 프로세스 종료 (PID $oldPid)" -ForegroundColor Yellow
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

# 재시작용 독립 스크립트 생성
@"
`$rpaPythonPath = "$rpaPythonPath"
`$logPath = "$logPath"
`$pidFile = "$pidFile"

New-Item -ItemType Directory -Path (Split-Path `$logPath) -Force | Out-Null

if (Test-Path `$pidFile) {
    `$oldPid = Get-Content `$pidFile
    Stop-Process -Id `$oldPid -Force -ErrorAction SilentlyContinue
    Remove-Item `$pidFile -Force -ErrorAction SilentlyContinue
}

`$process = Start-Process -FilePath "python.exe" ``
    -ArgumentList `$rpaPythonPath ``
    -WindowStyle Hidden ``
    -RedirectStandardOutput `$logPath ``
    -RedirectStandardError ("`$logPath.err") ``
    -PassThru ``
    -NoNewWindow
`$process.Id | Out-File -FilePath `$pidFile -Force
Write-Host "Craigslist RPA 시작 (PID: `$(`$process.Id))" -ForegroundColor Green
"@ | Out-File -FilePath $scriptPath -Encoding UTF8 -Force

# 백그라운드 실행 (NoNewWindow + Redirect로 완전 숨김)
$process = Start-Process -FilePath "python.exe" `
    -ArgumentList $rpaPythonPath `
    -WindowStyle Hidden `
    -RedirectStandardOutput $logPath `
    -RedirectStandardError $errPath `
    -PassThru `
    -NoNewWindow

$process.Id | Out-File -FilePath $pidFile -Encoding ASCII -Force

# 작업 스케줄러 등록 (부팅 시 자동 시작)
$taskName = "BRIDGE-Craigslist-RPA"
schtasks /delete /tn "BRIDGE\$taskName" /f 2>$null
schtasks /create /tn "BRIDGE\$taskName" `
    /tr "powershell -NoProfile -ExecutionPolicy Bypass -File '$scriptPath'" `
    /sc onstart /rl highest /f 2>$null | Out-Null

# PowerShell 프로필에 제어 함수 추가
$profilePath = $PROFILE
if (-not (Test-Path $profilePath)) { New-Item -ItemType File -Path $profilePath -Force | Out-Null }

$functions = @"

# BRIDGE Craigslist RPA 제어 함수
function Stop-CraiglistRPA {
    `$pidFile = "$pidFile"
    if (Test-Path `$pidFile) {
        `$p = Get-Content `$pidFile
        Stop-Process -Id `$p -Force -ErrorAction SilentlyContinue
        Remove-Item `$pidFile -Force
        Write-Host "RPA 중지 (PID `$p)" -ForegroundColor Green
    } else { Write-Host "실행 중이 아님" -ForegroundColor Red }
}

function Start-CraiglistRPA {
    & "$scriptPath"
}

function Restart-CraiglistRPA {
    Stop-CraiglistRPA; Start-Sleep 2; Start-CraiglistRPA
}

function Get-CraiglistRPA-Status {
    `$pidFile = "$pidFile"
    if (Test-Path `$pidFile) {
        `$p = Get-Content `$pidFile
        `$proc = Get-Process -Id `$p -ErrorAction SilentlyContinue
        if (`$proc) {
            Write-Host "실행 중 (PID: `$p  RAM: `$([math]::Round(`$proc.WorkingSet/1MB))MB)" -ForegroundColor Green
        } else { Write-Host "좀비 PID (파일만 존재)" -ForegroundColor Yellow }
    } else { Write-Host "실행 중이 아님" -ForegroundColor Red }
}
"@

if (-not (Select-String -Path $profilePath -Pattern "Stop-CraiglistRPA" -ErrorAction SilentlyContinue)) {
    Add-Content -Path $profilePath -Value $functions
}

Write-Host ""
Write-Host "BRIDGE Craigslist RPA 백그라운드 시작 완료" -ForegroundColor Green
Write-Host "PID    : $($process.Id)" -ForegroundColor Cyan
Write-Host "로그   : $logPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "제어 명령:" -ForegroundColor Cyan
Write-Host "  Get-CraiglistRPA-Status  상태 확인"
Write-Host "  Stop-CraiglistRPA        중지"
Write-Host "  Start-CraiglistRPA       시작"
Write-Host "  Restart-CraiglistRPA     재시작"
Write-Host ""
Write-Host "CMD 창 닫아도 계속 실행됨" -ForegroundColor Green
Write-Host "부팅 시 자동 시작 등록됨" -ForegroundColor Green
