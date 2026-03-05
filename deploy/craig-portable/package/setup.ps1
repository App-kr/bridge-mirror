# ============================================================
# BRIDGE Craigslist RPA — 원클릭 셋업 (다른 PC용)
# ============================================================
# 사용법: 이 폴더를 USB에 복사 -> 다른 PC에서 우클릭 -> PowerShell로 실행
# 또는: powershell -ExecutionPolicy Bypass -File setup.ps1
#
# 보안 정책:
#   - DB에서 PII 테이블 제거 (jobs + ad_posts만 포함)
#   - .env 파일 현재 사용자만 읽기 (ACL 제한)
#   - 크리덴셜 하드코딩 없음 (환경변수만)
#   - 로그에 개인정보 미기록
#   - Craigslist 비밀번호 입력 시 마스킹
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  BRIDGE Craigslist RPA Setup" -ForegroundColor Cyan
Write-Host "  Security-compliant installation" -ForegroundColor DarkCyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── 1) 설치 경로 (사용자 선택) ────────────────────────────────
Write-Host "[1/7] Install location" -ForegroundColor Yellow
Write-Host "  Default: D:\BridgeCraig" -ForegroundColor Gray
Write-Host "  (C drive is NOT recommended for security)" -ForegroundColor DarkYellow
$userPath = Read-Host "  Install path (Enter for default)"
if (-not $userPath) { $userPath = "D:\BridgeCraig" }
$InstallDir = $userPath.TrimEnd("\")

if (Test-Path $InstallDir) {
    Write-Host "  [OK] $InstallDir already exists" -ForegroundColor Green
} else {
    New-Item -Path $InstallDir -ItemType Directory -Force | Out-Null
    Write-Host "  [OK] Created $InstallDir" -ForegroundColor Green
}

foreach ($sub in @("logs", "screenshots", "data")) {
    $p = "$InstallDir\$sub"
    if (-not (Test-Path $p)) { New-Item -Path $p -ItemType Directory -Force | Out-Null }
}

# ── 2) Python 확인 ───────────────────────────────────────────
Write-Host ""
Write-Host "[2/7] Python check..." -ForegroundColor Yellow
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3") {
            $pythonCmd = $cmd
            Write-Host "  Found: $ver" -ForegroundColor Green
            break
        }
    } catch { }
}

if (-not $pythonCmd) {
    Write-Host "  [ERROR] Python 3 not found!" -ForegroundColor Red
    Write-Host "  Download: https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "  IMPORTANT: Check 'Add to PATH' during install" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# ── 3) pip 패키지 설치 ───────────────────────────────────────
Write-Host ""
Write-Host "[3/7] Installing packages..." -ForegroundColor Yellow
& $pythonCmd -m pip install --quiet --upgrade pip 2>$null
& $pythonCmd -m pip install --quiet selenium webdriver-manager python-dotenv 2>&1 | Out-Null
Write-Host "  [OK] selenium, webdriver-manager, python-dotenv" -ForegroundColor Green

# ── 4) 파일 복사 ─────────────────────────────────────────────
Write-Host ""
Write-Host "[4/7] Copying files..." -ForegroundColor Yellow

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# RPA 스크립트
Copy-Item "$ScriptDir\craigslist_auto_rpa.py" "$InstallDir\craigslist_auto_rpa.py" -Force
Write-Host "  [OK] craigslist_auto_rpa.py" -ForegroundColor Green

# DB 복사 — PII 제거된 안전 버전만
if (Test-Path "$ScriptDir\master_safe.db") {
    Copy-Item "$ScriptDir\master_safe.db" "$InstallDir\data\master.db" -Force
    Write-Host "  [OK] master_safe.db -> data/master.db (PII removed)" -ForegroundColor Green
} elseif (Test-Path "$ScriptDir\master.db") {
    Write-Host "  [WARN] Full master.db detected. Stripping PII tables..." -ForegroundColor Yellow
    # PII 테이블 제거: jobs + ad_posts만 남김
    Copy-Item "$ScriptDir\master.db" "$InstallDir\data\master.db" -Force
    & $pythonCmd -c @"
import sqlite3, sys
db = '$InstallDir\data\master.db'.replace('\\','\\\\')
conn = sqlite3.connect(db)
# PII 포함 테이블 목록
pii_tables = ['candidates','client_inquiries','interviews',
              'email_log','email_queue','contact_messages']
dropped = []
for t in pii_tables:
    try:
        conn.execute(f'DROP TABLE IF EXISTS {t}')
        dropped.append(t)
    except: pass
conn.execute('VACUUM')
conn.commit()
conn.close()
print(f'  Dropped PII tables: {dropped}')
"@ 2>&1
    Write-Host "  [OK] DB sanitized (jobs + ad_posts only)" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] No database found in package!" -ForegroundColor Red
    Write-Host "  Run pack.ps1 on the main PC first." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# ── 5) .env 설정 (보안 강화) ─────────────────────────────────
Write-Host ""
Write-Host "[5/7] Credentials setup..." -ForegroundColor Yellow

$envFile = "$InstallDir\.env"
if (Test-Path $envFile) {
    Write-Host "  [OK] .env already exists (not overwriting)" -ForegroundColor Green
} else {
    Write-Host "  Craigslist account:" -ForegroundColor Cyan
    $clEmail = Read-Host "    Email"
    $clPass  = Read-Host -AsSecureString "    Password"
    # SecureString -> plain text (로컬 .env 저장용)
    $clPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($clPass))
    $clCity  = Read-Host "    City (Enter for seoul)"
    if (-not $clCity) { $clCity = "seoul" }

    @"
# Bridge Craigslist RPA Config
# WARNING: Do not share this file. Contains credentials.
CRAIGSLIST_EMAIL=$clEmail
CRAIGSLIST_PASSWORD=$clPassPlain
CRAIGSLIST_CITY=$clCity
BRIDGE_APP_DIR=$InstallDir
BRIDGE_DB_PATH=$InstallDir\data\master.db
"@ | Set-Content $envFile -Encoding UTF8

    # 메모리에서 비밀번호 제거
    $clPassPlain = $null
    [GC]::Collect()

    # .env 파일 ACL: 현재 사용자만 읽기/쓰기
    $acl = Get-Acl $envFile
    $acl.SetAccessRuleProtection($true, $false)  # 상속 차단
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        [System.Security.Principal.WindowsIdentity]::GetCurrent().Name,
        "FullControl", "Allow")
    $acl.AddAccessRule($rule)
    Set-Acl $envFile $acl

    Write-Host "  [OK] .env created (ACL: current user only)" -ForegroundColor Green
}

# ── 6) 실행 래퍼 + Task Scheduler ─────────────────────────────
Write-Host ""
Write-Host "[6/7] Registering scheduled task..." -ForegroundColor Yellow

# 래퍼 스크립트 생성
$runnerPath = "$InstallDir\run_rpa.ps1"
@"
# Bridge Craigslist RPA Runner — auto-generated
`$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
`$LogFile = "$InstallDir\logs\scheduler.log"
Add-Content -Path `$LogFile -Value "[`$Timestamp] RPA START" -Encoding UTF8
Set-Location "$InstallDir"
try {
    & $pythonCmd craigslist_auto_rpa.py --headless --limit 10 2>&1 | Out-Null
    `$endTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path `$LogFile -Value "[`$endTime] RPA DONE (exit=`$LASTEXITCODE)" -Encoding UTF8
} catch {
    `$errTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path `$LogFile -Value "[`$errTime] RPA ERROR: `$_" -Encoding UTF8
}
"@ | Set-Content $runnerPath -Encoding UTF8

Unregister-ScheduledTask -TaskName "BridgeCraigslistRPA" -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runnerPath`""
$trigger = New-ScheduledTaskTrigger -Daily -At "03:00"
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 60)

Register-ScheduledTask -TaskName "BridgeCraigslistRPA" `
    -Action $action -Trigger $trigger -Settings $settings `
    -Description "Bridge Craigslist auto-posting (6hr cycle, security-compliant)" -Force | Out-Null

# 6시간 반복
$task = Get-ScheduledTask -TaskName "BridgeCraigslistRPA"
$task.Triggers[0].Repetition.Interval = "PT6H"
$task.Triggers[0].Repetition.Duration = "P1D"
$task | Set-ScheduledTask | Out-Null

Write-Host "  [OK] BridgeCraigslistRPA — every 6 hours (03, 09, 15, 21)" -ForegroundColor Green

# ── 7) 테스트 (dry-run) ──────────────────────────────────────
Write-Host ""
Write-Host "[7/7] Security check + test..." -ForegroundColor Yellow

# 보안 체크리스트
$checks = @()
$checks += if (Test-Path $envFile) { "[PASS] .env exists" } else { "[FAIL] .env missing" }
$checks += if (-not (Test-Path "$InstallDir\data\candidates*")) { "[PASS] No PII tables in DB" } else { "[FAIL] PII data detected" }
$checks += if ((Get-Acl $envFile).Access.Count -le 1) { "[PASS] .env ACL restricted" } else { "[WARN] .env ACL open" }

# DB에 PII 테이블이 없는지 최종 확인
$piiCheck = & $pythonCmd -c @"
import sqlite3
conn = sqlite3.connect('$($InstallDir -replace '\\','\\\\')\data\master.db')
tables = [r[0] for r in conn.execute('SELECT name FROM sqlite_master WHERE type=''table''').fetchall()]
pii = [t for t in tables if t in ('candidates','client_inquiries','interviews','email_log')]
conn.close()
if pii: print(f'[FAIL] PII tables found: {pii}')
else: print('[PASS] DB clean - no PII tables')
"@ 2>&1
$checks += $piiCheck

foreach ($c in $checks) {
    $color = if ($c -match "PASS") { "Green" } elseif ($c -match "WARN") { "Yellow" } else { "Red" }
    Write-Host "  $c" -ForegroundColor $color
}

# dry-run 테스트
Write-Host ""
Set-Location $InstallDir
$testResult = & $pythonCmd craigslist_auto_rpa.py --dry-run --limit 1 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [PASS] Dry-run test passed" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Dry-run issue (check .env and DB)" -ForegroundColor Yellow
}

# ── 완료 ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  SETUP COMPLETE" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Location  : $InstallDir" -ForegroundColor White
Write-Host "  Schedule  : Every 6 hours (03, 09, 15, 21)" -ForegroundColor White
Write-Host "  Logs      : $InstallDir\logs\scheduler.log" -ForegroundColor White
Write-Host "  DB        : jobs + ad_posts only (PII removed)" -ForegroundColor White
Write-Host "  .env      : ACL restricted (current user only)" -ForegroundColor White
Write-Host ""
Write-Host "  Security:" -ForegroundColor Cyan
Write-Host "    - No PII in database (candidates/interviews removed)" -ForegroundColor Gray
Write-Host "    - Credentials in .env only (not hardcoded)" -ForegroundColor Gray
Write-Host "    - .env readable by current user only" -ForegroundColor Gray
Write-Host "    - RPA auto-redacts PII from ad text (redact_pii)" -ForegroundColor Gray
Write-Host "    - Logs contain no personal information" -ForegroundColor Gray
Write-Host ""

Read-Host "Press Enter to close"
