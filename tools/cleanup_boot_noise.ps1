# 2026-04-20 — 부팅 시 보이는 창·대화상자 원인 정리 (안전: 전부 이동 백업)
$ErrorActionPreference = 'Continue'
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupRoot = "Q:\Claudework\bridge backup\boot_noise_$ts"
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null

function Move-Safe($src, $label) {
    if (Test-Path $src) {
        $dst = Join-Path $backupRoot $label
        New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
        Move-Item -Path $src -Destination $dst -Force -ErrorAction SilentlyContinue
        Write-Host "MOVED: $src -> $dst"
    }
}

Write-Host "=== HWP 자동복구 / 자동백업 파일 이동 ==="
$hwpAutoBackup = @(
    "$env:APPDATA\HNC\User\Shared110\HwpAutoBackup",
    "$env:APPDATA\HNC\User\Shared102\HwpAutoBackup",
    "$env:APPDATA\HNC\User\Shared96\HwpAutoBackup"
)
foreach ($p in $hwpAutoBackup) {
    if (Test-Path $p) {
        $dstDir = Join-Path $backupRoot (Split-Path $p -Leaf)
        New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
        Get-ChildItem $p -File -Force -ErrorAction SilentlyContinue | ForEach-Object {
            Move-Item $_.FullName -Destination $dstDir -Force -ErrorAction SilentlyContinue
            Write-Host "MOVED autobackup: $($_.FullName)"
        }
    }
}

Write-Host "`n=== Temp 내 HWP 잠금파일/자동저장 이동 ==="
Get-ChildItem "$env:LOCALAPPDATA\Temp" -Include '~$*.hwp','~$*.hwpx','*.asv' -File -Force -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    $dst = Join-Path $backupRoot "temp_hwp"
    New-Item -ItemType Directory -Force -Path $dst | Out-Null
    Move-Item $_.FullName -Destination $dst -Force -ErrorAction SilentlyContinue
    Write-Host "MOVED temp: $($_.FullName)"
}

Write-Host "`n=== Startup 의 ClaudeRestore.lnk.bak 이동 ==="
$claudeRestoreBak = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\ClaudeRestore.lnk.bak"
Move-Safe $claudeRestoreBak "ClaudeRestore.lnk.bak"

Write-Host "`n=== BRIDGE_GDrive_Backup Task — 창 숨김으로 변경 ==="
try {
    $t = Get-ScheduledTask -TaskName 'BRIDGE_GDrive_Backup' -ErrorAction Stop
    $newAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "& ''Q:\Claudework\bridge base\tools\run_gdrive_backup.bat''"'
    Set-ScheduledTask -TaskName 'BRIDGE_GDrive_Backup' -Action $newAction | Out-Null
    Write-Host "MODIFIED: BRIDGE_GDrive_Backup -> powershell Hidden"
} catch {
    Write-Host "SKIP: BRIDGE_GDrive_Backup not found"
}
try {
    $t = Get-ScheduledTask -TaskName 'BRIDGE_GDrive_Backup_Frequent' -ErrorAction Stop
    $newAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "& ''Q:\Claudework\bridge base\tools\run_gdrive_backup.bat''"'
    Set-ScheduledTask -TaskName 'BRIDGE_GDrive_Backup_Frequent' -Action $newAction | Out-Null
    Write-Host "MODIFIED: BRIDGE_GDrive_Backup_Frequent -> powershell Hidden"
} catch {
    Write-Host "SKIP: BRIDGE_GDrive_Backup_Frequent not found"
}

Write-Host "`n=== 결과 ==="
Write-Host "백업 폴더: $backupRoot"
Get-ChildItem $backupRoot -Recurse -ErrorAction SilentlyContinue | Select FullName, Length | Format-Table -AutoSize
