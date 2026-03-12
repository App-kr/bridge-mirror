# Claude UserPromptSubmit hook에서 호출됨
# 데몬이 이미 실행 중이면 SKIP, 아니면 백그라운드 시작

$daemonName = "BridgeBackupDaemon"
$daemonScript = "Q:\Claudework\bridge base\tools\bridge-5min-backup.ps1"
$lockFile = "$env:TEMP\bridge_backup_daemon.lock"

# 이미 실행 중 확인 (lock 파일 + 프로세스 ID 체크)
if (Test-Path $lockFile) {
    $pid_stored = Get-Content $lockFile -ErrorAction SilentlyContinue
    $running = Get-Process -Id $pid_stored -ErrorAction SilentlyContinue
    if ($running) { exit 0 }  # 이미 실행중 -> 스킵
}

# 백그라운드로 데몬 시작 (숨김 창)
$proc = Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$daemonScript`"" -PassThru -WindowStyle Hidden
$proc.Id | Out-File $lockFile -Encoding ASCII -Force

# 로그
$log = "$env:APPDATA\AntiGravity\SessionBackups\daemon-start.log"
"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] 데몬 시작 PID=$($proc.Id)" |
    Add-Content -Path $log -Encoding UTF8
