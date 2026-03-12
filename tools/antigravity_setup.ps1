$agConfigPath = "$env:APPDATA\AntiGravity"
$settingsFile = "$agConfigPath\settings.json"
$sessionBackupPath = "$agConfigPath\SessionBackups"

New-Item -ItemType Directory -Path $sessionBackupPath -Force | Out-Null

$config = @{
    "session_recovery" = $true
    "auto_resume" = $true
    "persistenceStrategy" = "persistedWindowLayout"
    "disableAnimations" = $false
    "sessionBackupInterval" = 30000
    "autoRestoreLastSession" = $true
    "crashRecoveryEnabled" = $true
    "terminal" = @{
        "persistSession" = $true
        "autoSaveHistory" = $true
        "sessionTimeout" = 0
        "enableSessionRestore" = $true
    }
    "window" = @{
        "rememberWindowState" = $true
        "rememberPaneLayout" = $true
        "rememberOpenTabs" = $true
    }
} | ConvertTo-Json -Depth 4

$config | Out-File -FilePath $settingsFile -Encoding UTF8 -Force

$recoveryScript = @"
@echo off
setlocal enabledelayedexpansion
:check_loop
tasklist | find /i "AntiGravity.exe" >nul 2>&1
if errorlevel 1 (
    echo [!time!] AntiGravity 복구 모드 실행...
    if exist "%APPDATA%\AntiGravity\SessionBackups\latest-session.json" (
        start "" "%APPDATA%\AntiGravity\antigravity.exe" --recover-session
    ) else (
        start "" "%APPDATA%\AntiGravity\antigravity.exe"
    )
    timeout /t 5 /nobreak
)
timeout /t 60 /nobreak
goto check_loop
"@

$recoveryScript | Out-File -FilePath "$agConfigPath\auto-recovery.bat" -Encoding ASCII -Force

$psMonitor = @"
`$agExePath = "$env:APPDATA\AntiGravity\antigravity.exe"
`$sessionBackup = "$sessionBackupPath\latest-session.json"

while (`$true) {
    try {
        `$process = Get-Process -Name "AntiGravity" -ErrorAction SilentlyContinue
        if (-not `$process) {
            Write-Host "[`$(Get-Date -Format 'HH:mm:ss')] AntiGravity 복구 중..."
            if (Test-Path `$sessionBackup) {
                & `$agExePath --restore-session
            } else {
                & `$agExePath
            }
            Start-Sleep -Seconds 10
        }
        Start-Sleep -Seconds 30
    }
    catch {
        Start-Sleep -Seconds 60
    }
}
"@

$psMonitor | Out-File -FilePath "$agConfigPath\session-monitor.ps1" -Encoding UTF8 -Force

schtasks /create /tn "AntiGravity\AutoRecovery" /tr "powershell -NoProfile -ExecutionPolicy Bypass -File '$agConfigPath\session-monitor.ps1'" /sc onlogon /rl highest /f 2>$null

$psProfile = $PROFILE
if (-not (Test-Path $psProfile)) { New-Item -ItemType File -Path $psProfile -Force | Out-Null }

$backupFunction = @"

function Backup-AntiGravitySession {
    `$sessionPath = "`$env:APPDATA\AntiGravity\SessionBackups"
    `$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    `$backupFile = "`$sessionPath\session-`$timestamp.json"
    if (Test-Path "`$sessionPath\latest-session.json") {
        Copy-Item -Path "`$sessionPath\latest-session.json" -Destination `$backupFile -Force
        Write-Host "세션 백업: `$backupFile" -ForegroundColor Green
    }
}
function Restore-AntiGravitySession {
    `$sessionPath = "`$env:APPDATA\AntiGravity\SessionBackups"
    `$latest = Get-ChildItem -Path `$sessionPath -Filter "session-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (`$latest) {
        Copy-Item -Path `$latest.FullName -Destination "`$sessionPath\latest-session.json" -Force
        & "`$env:APPDATA\AntiGravity\antigravity.exe" --restore-session
        Write-Host "세션 복구 실행: `$(`$latest.Name)" -ForegroundColor Green
    }
}
"@

if (-not (Select-String -Path $psProfile -Pattern "Backup-AntiGravitySession" -ErrorAction SilentlyContinue)) {
    Add-Content -Path $psProfile -Value $backupFunction
}

Write-Host "AntiGravity 세션 자동복구 설정 완료" -ForegroundColor Green
Write-Host "설정: $settingsFile" -ForegroundColor Cyan
Write-Host "모니터: $agConfigPath\session-monitor.ps1" -ForegroundColor Cyan
