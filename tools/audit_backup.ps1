$BASE = "Q:\Claudework\bridge base"
$TOOLS = "$BASE\tools"
$SEP = "=" * 60

Write-Host ("`n" + $SEP)
Write-Host ("BRIDGE BACKUP FORENSIC AUDIT -- " + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
Write-Host ($SEP + "`n")

# 1
Write-Host "[1] TOOLS directory files"
Get-ChildItem "$TOOLS" -Recurse -File -ErrorAction SilentlyContinue |
  Select-Object FullName, Length, LastWriteTime |
  Format-Table -AutoSize

# 2
Write-Host "`n[2] Task Scheduler -- Bridge related tasks"
Get-ScheduledTask -ErrorAction SilentlyContinue |
  Where-Object { $_.TaskName -match "bridge|guardian|monitor|backup|render" -or
                 $_.TaskPath -match "bridge" } |
  Select-Object TaskName, TaskPath, State,
    @{N="LastRun";E={(Get-ScheduledTaskInfo $_.TaskName -ErrorAction SilentlyContinue).LastRunTime}},
    @{N="LastResult";E={(Get-ScheduledTaskInfo $_.TaskName -ErrorAction SilentlyContinue).LastTaskResult}} |
  Format-Table -AutoSize

# 3
Write-Host "`n[3] Running Python processes"
Get-Process -Name "python","pythonw" -ErrorAction SilentlyContinue |
  Select-Object Id, Name, CPU, WorkingSet, Path, StartTime |
  Format-Table -AutoSize

# 4
Write-Host "`n[4] Autostart entries"
@(
  "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run",
  "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run"
) | ForEach-Object {
  Write-Host ("  REG: " + $_)
  Get-ItemProperty $_ -ErrorAction SilentlyContinue |
    Get-Member -MemberType NoteProperty |
    Where-Object { $_.Name -notmatch "^PS" } |
    ForEach-Object { "    " + $_.Name }
}
Write-Host "  STARTUP FOLDER:"
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup" -ErrorAction SilentlyContinue |
  Select-Object Name, LastWriteTime | Format-Table -AutoSize

# 5
Write-Host "`n[5] Backup-related files/folders"
Get-ChildItem "$BASE" -Recurse -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match "backup|bak|guardian_state|snapshot" } |
  Select-Object FullName, Length, LastWriteTime | Format-Table -AutoSize

# 6
Write-Host "`n[6] CLAUDE.md backup/autorun rules"
$claudemd = Get-Content "$BASE\CLAUDE.md" -ErrorAction SilentlyContinue
$claudemd | Select-String -Pattern "backup|guardian|scheduler|auto.?backup" -Context 2,2

# 7
Write-Host "`n[7] Git backup/guardian/monitor commit history"
Set-Location "$BASE"
git log --oneline --all --grep="backup|guardian|monitor|scheduler" 2>$null | Select-Object -First 20

# 8
Write-Host "`n[8] render_monitor.py top 80 lines"
Get-Content "$TOOLS\render_monitor.py" -TotalCount 80 -ErrorAction SilentlyContinue

# 9
Write-Host "`n[9] Log files"
Get-ChildItem "$TOOLS\monitor_logs" -ErrorAction SilentlyContinue |
  Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize
if (Test-Path "$TOOLS\monitor_logs") {
  Get-ChildItem "$TOOLS\monitor_logs\*.log" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host ("  LOG: " + $_.Name + " -- last 10 lines:")
    Get-Content $_.FullName -Tail 10 -ErrorAction SilentlyContinue
  }
}

Write-Host ("`n" + $SEP + "`nAUDIT COMPLETE`n" + $SEP)
