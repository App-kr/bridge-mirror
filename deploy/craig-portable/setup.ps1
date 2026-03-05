# ============================================================
# BRIDGE Craigslist RPA — 원클릭 셋업 (다른 PC용)
# ============================================================
# 사용법: 이 폴더를 USB에 복사 → 다른 PC에서 우클릭 → PowerShell로 실행
# 또는: powershell -ExecutionPolicy Bypass -File setup.ps1
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  BRIDGE Craigslist RPA Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── 1) 설치 경로 ──────────────────────────────────────────────
$InstallDir = "C:\BridgeCraig"

if (Test-Path $InstallDir) {
    Write-Host "[OK] $InstallDir already exists" -ForegroundColor Green
} else {
    New-Item -Path $InstallDir -ItemType Directory -Force | Out-Null
    Write-Host "[OK] Created $InstallDir" -ForegroundColor Green
}

foreach ($sub in @("logs", "screenshots", "data")) {
    $p = "$InstallDir\$sub"
    if (-not (Test-Path $p)) { New-Item -Path $p -ItemType Directory -Force | Out-Null }
}

# ── 2) Python 확인 ───────────────────────────────────────────
Write-Host ""
Write-Host "[2/6] Python check..." -ForegroundColor Yellow
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
    Write-Host "  Download from: https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "  Install with 'Add to PATH' checked" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# ── 3) pip 패키지 설치 ───────────────────────────────────────
Write-Host ""
Write-Host "[3/6] Installing packages..." -ForegroundColor Yellow
& $pythonCmd -m pip install --quiet --upgrade pip 2>$null
& $pythonCmd -m pip install --quiet selenium webdriver-manager python-dotenv 2>&1 | Out-Null
Write-Host "  [OK] selenium, webdriver-manager, python-dotenv" -ForegroundColor Green

# ── 4) 파일 복사 ─────────────────────────────────────────────
Write-Host ""
Write-Host "[4/6] Copying files..." -ForegroundColor Yellow

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# RPA 스크립트
Copy-Item "$ScriptDir\craigslist_auto_rpa.py" "$InstallDir\craigslist_auto_rpa.py" -Force
Write-Host "  [OK] craigslist_auto_rpa.py" -ForegroundColor Green

# DB 복사 (있으면)
if (Test-Path "$ScriptDir\master.db") {
    Copy-Item "$ScriptDir\master.db" "$InstallDir\data\master.db" -Force
    Write-Host "  [OK] master.db -> data/" -ForegroundColor Green
} else {
    Write-Host "  [WARN] master.db not found in package. Copy it manually to $InstallDir\data\" -ForegroundColor Yellow
}

# .env 설정
$envFile = "$InstallDir\.env"
if (Test-Path $envFile) {
    Write-Host "  [OK] .env already exists (not overwriting)" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  Craigslist account setup:" -ForegroundColor Cyan
    $clEmail = Read-Host "    Craigslist Email"
    $clPass  = Read-Host "    Craigslist Password"
    $clCity  = Read-Host "    City (default: seoul)"
    if (-not $clCity) { $clCity = "seoul" }

    @"
# Bridge Craigslist RPA Config
CRAIGSLIST_EMAIL=$clEmail
CRAIGSLIST_PASSWORD=$clPass
CRAIGSLIST_CITY=$clCity
BRIDGE_APP_DIR=$InstallDir
BRIDGE_DB_PATH=$InstallDir\data\master.db
"@ | Set-Content $envFile -Encoding UTF8

    Write-Host "  [OK] .env created" -ForegroundColor Green
}

# 실행 래퍼 스크립트
$runnerPath = "$InstallDir\run_rpa.ps1"
@"
# Bridge Craigslist RPA Runner
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
Write-Host "  [OK] run_rpa.ps1 created" -ForegroundColor Green

# ── 5) Task Scheduler 등록 ───────────────────────────────────
Write-Host ""
Write-Host "[5/6] Registering scheduled task..." -ForegroundColor Yellow

Unregister-ScheduledTask -TaskName "BridgeCraigslistRPA" -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runnerPath`""

$trigger = New-ScheduledTaskTrigger -Daily -At "03:00"
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 60)

Register-ScheduledTask -TaskName "BridgeCraigslistRPA" `
    -Action $action -Trigger $trigger -Settings $settings `
    -Description "Bridge Craigslist auto-posting (6hr cycle)" -Force | Out-Null

# 6시간 반복
$task = Get-ScheduledTask -TaskName "BridgeCraigslistRPA"
$task.Triggers[0].Repetition.Interval = "PT6H"
$task.Triggers[0].Repetition.Duration = "P1D"
$task | Set-ScheduledTask | Out-Null

Write-Host "  [OK] BridgeCraigslistRPA — every 6 hours (03, 09, 15, 21)" -ForegroundColor Green

# ── 6) 테스트 (dry-run) ──────────────────────────────────────
Write-Host ""
Write-Host "[6/6] Test run (dry-run)..." -ForegroundColor Yellow

Set-Location $InstallDir
$testResult = & $pythonCmd craigslist_auto_rpa.py --dry-run --limit 1 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Dry-run passed!" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Dry-run issue (check .env and master.db)" -ForegroundColor Yellow
    Write-Host "  $testResult" -ForegroundColor Gray
}

# ── 완료 ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  SETUP COMPLETE!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Install dir : $InstallDir" -ForegroundColor White
Write-Host "  Schedule    : Every 6 hours (03, 09, 15, 21)" -ForegroundColor White
Write-Host "  Logs        : $InstallDir\logs\scheduler.log" -ForegroundColor White
Write-Host ""
Write-Host "  Manual commands:" -ForegroundColor Cyan
Write-Host "    cd $InstallDir" -ForegroundColor Gray
Write-Host "    python craigslist_auto_rpa.py --dry-run --limit 1   # test" -ForegroundColor Gray
Write-Host "    python craigslist_auto_rpa.py --headless --limit 5  # real" -ForegroundColor Gray
Write-Host ""

Read-Host "Press Enter to close"
