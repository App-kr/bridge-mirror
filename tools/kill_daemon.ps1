$lockFile = "C:\Users\Scarlett\AppData\Local\Temp\qdrive_backup.lock"
if (Test-Path $lockFile) {
    $pid_stored = Get-Content $lockFile -ErrorAction SilentlyContinue
    Write-Host "Lock 파일 PID: $pid_stored"
    $proc = Get-Process -Id $pid_stored -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "프로세스 발견: $($proc.Name) [$pid_stored] => 종료"
        Stop-Process -Id $pid_stored -Force
        Write-Host "daemon 종료 완료"
    } else {
        Write-Host "daemon이 이미 종료된 상태"
    }
    Remove-Item $lockFile -Force
    Write-Host "lock 파일 삭제"
} else {
    Write-Host "lock 파일 없음"
}

# 혹시 남은 backup_daemon python 프로세스 확인
$daemons = Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like "*backup_daemon*" }
if ($daemons) {
    foreach ($d in $daemons) {
        Write-Host "추가 daemon PID=$($d.ProcessId) => 종료"
        Stop-Process -Id $d.ProcessId -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "추가 backup_daemon 프로세스 없음"
}

# 현재 _BACKUP 상태 확인
$count = (Get-ChildItem "Q:\Claudework\_BACKUP" -Directory -ErrorAction SilentlyContinue).Count
Write-Host ""
Write-Host "_BACKUP 현재 스냅샷 수: $count"
