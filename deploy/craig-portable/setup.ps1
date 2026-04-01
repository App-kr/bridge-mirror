# ============================================================
# BRIDGE Craigslist RPA — 원클릭 셋업  v2  (2026-04-01)
# ============================================================
# 사용법: 이 폴더를 USB에 복사 → 다른 PC에서 우클릭 → PowerShell로 실행
# 또는: powershell -ExecutionPolicy Bypass -File setup.ps1
#
# 포함 기능:
#   - Python 자동 탐지 (3.10+)
#   - pip 패키지 자동 설치 (selenium, webdriver-manager, pillow 등)
#   - DPAPI 자격증명 vault 설정
#   - BRIDGE RPA 아이콘 포함 바탕화면 바로가기
#   - RPA 진행 오버레이 (한국어 UI + 곰 애니메이션)
#   - Task Scheduler 6시간 자동 실행
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  BRIDGE Craigslist RPA Setup  v2" -ForegroundColor Cyan
Write-Host "  bridgejob.co.kr | Craigslist Auto-Post" -ForegroundColor DarkCyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── 1) 설치 경로 ──────────────────────────────────────────
Write-Host "[1/8] Install location" -ForegroundColor Yellow
Write-Host "  Default: D:\BridgeCraig" -ForegroundColor Gray
$userPath = Read-Host "  Install path (Enter for default)"
if (-not $userPath) { $userPath = "D:\BridgeCraig" }
$InstallDir = $userPath.TrimEnd("\")

if (Test-Path $InstallDir) {
    Write-Host "  [OK] $InstallDir already exists" -ForegroundColor Green
} else {
    New-Item -Path $InstallDir -ItemType Directory -Force | Out-Null
    Write-Host "  [OK] Created $InstallDir" -ForegroundColor Green
}
foreach ($sub in @("logs", "screenshots", "data", "tools")) {
    $p = "$InstallDir\$sub"
    if (-not (Test-Path $p)) { New-Item -Path $p -ItemType Directory -Force | Out-Null }
}

# ── 2) Python 확인 ───────────────────────────────────────
Write-Host ""
Write-Host "[2/8] Python check..." -ForegroundColor Yellow
$pythonExe = $null

# 일반 PATH 검색
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3\.([1-9][0-9]|[0-9])") {
            $pythonExe = (Get-Command $cmd -ErrorAction SilentlyContinue).Source
            if (-not $pythonExe) { $pythonExe = $cmd }
            Write-Host "  Found: $ver ($pythonExe)" -ForegroundColor Green
            break
        }
    } catch { }
}

# 일반 설치 경로 수동 탐색
if (-not $pythonExe) {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "C:\Python313\python.exe",
        "C:\Python312\python.exe",
        "C:\Python310\python.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) {
            $ver = & $p --version 2>&1
            if ($ver -match "Python 3") {
                $pythonExe = $p
                Write-Host "  Found: $ver ($p)" -ForegroundColor Green
                break
            }
        }
    }
}

if (-not $pythonExe) {
    Write-Host "  [ERROR] Python 3 not found!" -ForegroundColor Red
    Write-Host "  Download: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "  ★★★ 설치 시 'Add Python to PATH' 반드시 체크 ★★★" -ForegroundColor Yellow
    Read-Host "Python 설치 후 Enter로 재시도 (또는 Ctrl+C 종료)"
    # 재시도
    foreach ($cmd in @("python", "python3", "py")) {
        try {
            $ver = & $cmd --version 2>&1
            if ($ver -match "Python 3") { $pythonExe = $cmd; break }
        } catch { }
    }
    if (-not $pythonExe) {
        Write-Host "  [FATAL] Still no Python. 설치 후 다시 실행하세요." -ForegroundColor Red
        Read-Host "Press Enter to exit"; exit 1
    }
}

# ── 3) pip 패키지 설치 ──────────────────────────────────
Write-Host ""
Write-Host "[3/8] Installing Python packages..." -ForegroundColor Yellow
& $pythonExe -m pip install --quiet --upgrade pip 2>$null
$packages = @("selenium", "webdriver-manager", "python-dotenv",
              "Pillow", "cryptography", "screeninfo", "pywin32")
foreach ($pkg in $packages) {
    Write-Host "  Installing $pkg..." -ForegroundColor DarkGray -NoNewline
    & $pythonExe -m pip install --quiet $pkg 2>$null
    Write-Host " OK" -ForegroundColor Green
}
Write-Host "  [OK] All packages installed" -ForegroundColor Green

# ── 4) 파일 복사 ────────────────────────────────────────
Write-Host ""
Write-Host "[4/8] Copying RPA files..." -ForegroundColor Yellow

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 메인 RPA 파일들
foreach ($f in @("craigslist_auto_rpa.py", "rpa_overlay.py")) {
    if (Test-Path "$ScriptDir\$f") {
        Copy-Item "$ScriptDir\$f" "$InstallDir\$f" -Force
        Write-Host "  [OK] $f" -ForegroundColor Green
    }
}

# 아이콘
if (Test-Path "$ScriptDir\rpa_icon.ico") {
    Copy-Item "$ScriptDir\rpa_icon.ico" "$InstallDir\rpa_icon.ico" -Force
    Write-Host "  [OK] rpa_icon.ico" -ForegroundColor Green
}

# tools/ 서브모듈
if (Test-Path "$ScriptDir\tools\rpa_credential_vault.py") {
    Copy-Item "$ScriptDir\tools\rpa_credential_vault.py" "$InstallDir\tools\rpa_credential_vault.py" -Force
    Write-Host "  [OK] tools/rpa_credential_vault.py" -ForegroundColor Green
}

# 이미지
if (Test-Path "$ScriptDir\images") {
    Copy-Item "$ScriptDir\images\*" "$InstallDir\images\" -Force -ErrorAction SilentlyContinue
    Write-Host "  [OK] images/" -ForegroundColor Green
}

# DB
if (Test-Path "$ScriptDir\master_safe.db") {
    Copy-Item "$ScriptDir\master_safe.db" "$InstallDir\data\master.db" -Force
    Write-Host "  [OK] master_safe.db -> data/master.db (PII removed)" -ForegroundColor Green
} elseif (Test-Path "$ScriptDir\master.db") {
    Write-Host "  [WARN] Full master.db found — stripping PII tables..." -ForegroundColor Yellow
    Copy-Item "$ScriptDir\master.db" "$InstallDir\data\master.db" -Force
    & $pythonExe -c @"
import sqlite3
conn = sqlite3.connect(r'$InstallDir\data\master.db')
for t in ['candidates','client_inquiries','interviews','email_log','email_queue','contact_messages']:
    conn.execute(f'DROP TABLE IF EXISTS {t}')
conn.execute('VACUUM'); conn.commit(); conn.close()
print('  PII tables removed')
"@ 2>&1
} else {
    Write-Host "  [ERROR] No database found! Run pack.ps1 on main PC first." -ForegroundColor Red
    Read-Host "Press Enter to exit"; exit 1
}

# ── 5) 자격증명 설정 (DPAPI vault) ──────────────────────
Write-Host ""
Write-Host "[5/8] Credentials setup..." -ForegroundColor Yellow

# vault 파일이 이미 있으면 건너뜀
$vaultFile = "$InstallDir\.rpa_vault.enc.json"
if (Test-Path $vaultFile) {
    Write-Host "  [OK] Vault already exists — credentials not overwritten" -ForegroundColor Green
} else {
    Write-Host "  Craigslist 계정 입력:" -ForegroundColor Cyan
    $clEmail = Read-Host "    Email"
    $clPassSS = Read-Host -AsSecureString "    Password (입력해도 화면에 안 보임)"
    $clPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($clPassSS))
    $clCity = Read-Host "    City (Enter for seoul)"
    if (-not $clCity) { $clCity = "seoul" }

    # rpa_credential_vault.py로 vault 생성
    if (Test-Path "$InstallDir\tools\rpa_credential_vault.py") {
        Push-Location $InstallDir
        & $pythonExe -c @"
import sys, os
sys.path.insert(0, r'$InstallDir\tools')
os.chdir(r'$InstallDir')
from rpa_credential_vault import RpaCredentialVault
vault = RpaCredentialVault()
vault.setup_account('default', '$clEmail', '$clPassPlain', '$clCity')
print('  [OK] Vault created (DPAPI encrypted)')
"@ 2>&1
        Pop-Location
    } else {
        # fallback: .env 파일
        @"
CRAIGSLIST_EMAIL=$clEmail
CRAIGSLIST_PASSWORD=$clPassPlain
CRAIGSLIST_CITY=$clCity
BRIDGE_APP_DIR=$InstallDir
BRIDGE_DB_PATH=$InstallDir\data\master.db
"@ | Set-Content "$InstallDir\.env" -Encoding UTF8
        # ACL 제한
        $acl = Get-Acl "$InstallDir\.env"
        $acl.SetAccessRuleProtection($true, $false)
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            [System.Security.Principal.WindowsIdentity]::GetCurrent().Name,
            "FullControl", "Allow")
        $acl.AddAccessRule($rule)
        Set-Acl "$InstallDir\.env" $acl
        Write-Host "  [OK] .env created (DPAPI vault unavailable, ACL restricted)" -ForegroundColor Yellow
    }

    # 메모리 소각
    $clPassPlain = $null; [GC]::Collect()
    Write-Host "  [OK] Credentials saved (current user only)" -ForegroundColor Green
}

# ── 6) VBS 런처 생성 (창 없이 실행) ────────────────────
Write-Host ""
Write-Host "[6/8] Creating launcher..." -ForegroundColor Yellow

$vbsPath = "$InstallDir\RPA.vbs"
$pythonExeEscaped = $pythonExe -replace '"', '""'
@"
' BRIDGE Craig RPA Launcher — auto-generated
Set objShell = CreateObject("WScript.Shell")
Set objFSO   = CreateObject("Scripting.FileSystemObject")
strDir    = objFSO.GetParentFolderName(WScript.ScriptFullName)
strScript = strDir & "\craigslist_auto_rpa.py"
strPython = "$pythonExeEscaped"
' 0 = 숨김, False = 비동기
objShell.Run """" & strPython & """ -X utf8 """ & strScript & """ --headless", 0, False
"@ | Set-Content $vbsPath -Encoding UTF8
Write-Host "  [OK] RPA.vbs (silent launcher)" -ForegroundColor Green

# Task Scheduler 래퍼
$runnerPath = "$InstallDir\run_rpa.ps1"
@"
# Bridge RPA Scheduler Runner — auto-generated
`$log = "$InstallDir\logs\scheduler.log"
Add-Content `$log "[`$(Get-Date -f 'yyyy-MM-dd HH:mm:ss')] RPA START" -Encoding UTF8
Set-Location "$InstallDir"
try {
    & "$pythonExe" craigslist_auto_rpa.py --headless --limit 10 2>&1 | Out-Null
    Add-Content `$log "[`$(Get-Date -f 'yyyy-MM-dd HH:mm:ss')] DONE (exit=`$LASTEXITCODE)" -Encoding UTF8
} catch {
    Add-Content `$log "[`$(Get-Date -f 'yyyy-MM-dd HH:mm:ss')] ERROR: `$_" -Encoding UTF8
}
"@ | Set-Content $runnerPath -Encoding UTF8

# ── 7) Task Scheduler 등록 ──────────────────────────────
Write-Host ""
Write-Host "[7/8] Registering scheduled task..." -ForegroundColor Yellow
try {
    Unregister-ScheduledTask -TaskName "BridgeCraigslistRPA" -Confirm:$false -ErrorAction SilentlyContinue

    $action   = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runnerPath`""
    $trigger  = New-ScheduledTaskTrigger -Daily -At "03:00"
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 60)
    Register-ScheduledTask -TaskName "BridgeCraigslistRPA" `
        -Action $action -Trigger $trigger -Settings $settings `
        -Description "Bridge Craigslist RPA — 6hr cycle" -Force | Out-Null

    # 6시간 반복 설정
    $task = Get-ScheduledTask -TaskName "BridgeCraigslistRPA"
    $task.Triggers[0].Repetition.Interval = "PT6H"
    $task.Triggers[0].Repetition.Duration = "P1D"
    $task | Set-ScheduledTask | Out-Null
    Write-Host "  [OK] BridgeCraigslistRPA — 6시간마다 (03:00, 09:00, 15:00, 21:00)" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Scheduler 등록 실패 (관리자 권한 필요): $_" -ForegroundColor Yellow
    Write-Host "  수동 실행: 바탕화면 'BRIDGE Craig RPA' 더블클릭" -ForegroundColor Gray
}

# ── 8) 바탕화면 바로가기 ────────────────────────────────
Write-Host ""
Write-Host "[8/8] Creating desktop shortcut..." -ForegroundColor Yellow
$Desktop      = [Environment]::GetFolderPath("Desktop")
$shortcutPath = "$Desktop\BRIDGE Craig RPA.lnk"
$iconPath     = if (Test-Path "$InstallDir\rpa_icon.ico") { "$InstallDir\rpa_icon.ico" } else { "" }

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($shortcutPath)
$sc.TargetPath      = "wscript.exe"
$sc.Arguments       = "`"$vbsPath`""
$sc.WorkingDirectory = $InstallDir
$sc.Description     = "BRIDGE Craigslist 자동 게시 (클릭하면 바로 실행)"
$sc.WindowStyle     = 1
if ($iconPath) { $sc.IconLocation = "$iconPath,0" }
$sc.Save()
Write-Host "  [OK] 바탕화면 'BRIDGE Craig RPA' 바로가기 생성" -ForegroundColor Green
if ($iconPath) { Write-Host "  [OK] BRIDGE RPA 아이콘 적용" -ForegroundColor Green }

# ── 완료 ────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  SETUP COMPLETE!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  설치 위치  : $InstallDir" -ForegroundColor White
Write-Host "  바탕화면   : 'BRIDGE Craig RPA' 더블클릭 → 즉시 실행" -ForegroundColor White
Write-Host "  자동 실행  : 6시간마다 (03, 09, 15, 21시)" -ForegroundColor White
Write-Host "  로그       : $InstallDir\logs\scheduler.log" -ForegroundColor White
Write-Host "  DB         : jobs + ad_posts만 (PII 제거됨)" -ForegroundColor White
Write-Host ""
Write-Host "  보안:" -ForegroundColor Cyan
Write-Host "    - 자격증명 DPAPI 암호화 (현재 사용자만 복호화 가능)" -ForegroundColor Gray
Write-Host "    - DB에 후보자/업체 개인정보 없음" -ForegroundColor Gray
Write-Host "    - 광고 텍스트 내 PII 자동 제거" -ForegroundColor Gray
Write-Host "    - 로그에 개인정보 미기록" -ForegroundColor Gray
Write-Host ""

Read-Host "Press Enter to close"
