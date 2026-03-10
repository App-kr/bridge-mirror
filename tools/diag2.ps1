# 1. BridgeRenderMonitor 오류 진단
Write-Host "=== [1] BridgeRenderMonitor schtasks ==="
schtasks /query /tn "BridgeRenderMonitor" /fo LIST /v

Write-Host "`n=== [1b] Get-ScheduledTaskInfo ==="
Get-ScheduledTaskInfo -TaskName "BridgeRenderMonitor" | Select-Object LastRunTime, LastTaskResult, NextRunTime

# 2. AutoBackup5min 실제 실행 명령 확인
Write-Host "`n=== [2] AutoBackup5min ==="
schtasks /query /tn "\Bridge\AutoBackup5min" /fo LIST /v

# 3. 분산 백업 현황
$BASE = "Q:\Claudework\bridge base"

Write-Host "`n=== [3a] root master.db.backup_* ==="
Get-ChildItem "$BASE\master.db.backup_*" -ErrorAction SilentlyContinue | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize

Write-Host "=== [3b] .backups\ ==="
Get-ChildItem "$BASE\.backups\" -Recurse -File -ErrorAction SilentlyContinue | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize

Write-Host "=== [3c] backups\ total ==="
Get-ChildItem "$BASE\backups\" -Recurse -File -ErrorAction SilentlyContinue |
  Measure-Object -Property Length -Sum | Select-Object Count, Sum

Write-Host "`n=== [3d] .hooks\auto_backup.py top 30 lines ==="
Get-Content "$BASE\.hooks\auto_backup.py" -TotalCount 30 -ErrorAction SilentlyContinue

Write-Host "`n=== [3e] .logs\auto_backup.log last 20 lines ==="
Get-Content "$BASE\.logs\auto_backup.log" -Tail 20 -ErrorAction SilentlyContinue
