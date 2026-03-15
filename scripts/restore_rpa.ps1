# BRIDGE RPA Restore Script (ASCII-safe)
$ErrorActionPreference = "Stop"
$BASE    = "Q:\Claudework\bridge base"
$PYTHON  = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe"
$PYTHONW = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\pythonw.exe"
$VBS     = "$BASE\start_craig.vbs"
$PS1     = "$BASE\scripts\run_craigslist_rpa.ps1"
$DESKTOP = [Environment]::GetFolderPath("Desktop")
$LOG     = "$BASE\logs\scheduler.log"

# STEP 1: Python check
if (-not (Test-Path $PYTHON)) { Write-Host "FAIL: python not found"; exit 1 }
Write-Host "OK: $(& $PYTHON --version 2>&1)"

# STEP 2: Rewrite run_craigslist_rpa.ps1 (Q drive path, explicit python)
$newPs1 = @'
chcp 65001 | Out-Null
$ProjectRoot = "Q:\Claudework\bridge base"
$PythonExe   = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe"
$LogFile     = "$ProjectRoot\logs\scheduler.log"
$Timestamp   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LogFile -Value "[$Timestamp] SCHED START" -Encoding UTF8
Set-Location $ProjectRoot
try {
    & $PythonExe "craigslist_auto_rpa.py" "--headless" "--limit" "10" 2>&1 | Out-Null
    $exitCode = $LASTEXITCODE
    $endTime  = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "[$endTime] SCHED DONE exit=$exitCode" -Encoding UTF8
} catch {
    Add-Content -Path $LogFile -Value "[(Get-Date -Format 'HH:mm:ss')] SCHED ERR: $_" -Encoding UTF8
}
'@
$newPs1 | Out-File -FilePath $PS1 -Encoding UTF8
Write-Host "OK: ps1 updated"

# STEP 3: Register scheduled tasks
$tr = "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$PS1`""

# Delete old (ignore errors if not found)
$ErrorActionPreference = "Continue"
schtasks /Delete /TN "BridgeCraigslistRPA"    /F 2>&1 | Out-Null
schtasks /Delete /TN "BridgeCraigslistRPA_6H" /F 2>&1 | Out-Null
$ErrorActionPreference = "Stop"

# Onlogon (2min delay)
schtasks /Create /TN "BridgeCraigslistRPA"    /TR $tr /SC ONLOGON /DELAY 0002:00 /RL HIGHEST /F
# Every 6 hours
schtasks /Create /TN "BridgeCraigslistRPA_6H" /TR $tr /SC HOURLY  /MO 6          /RL HIGHEST /F

Write-Host "OK: tasks registered"

# STEP 4: Desktop shortcut
$lnkPath = "$DESKTOP\BRIDGE Craig RPA.lnk"
$ws      = New-Object -ComObject WScript.Shell
$lnk     = $ws.CreateShortcut($lnkPath)
$lnk.TargetPath       = "wscript.exe"
$lnk.Arguments        = "`"$VBS`""
$lnk.WorkingDirectory = $BASE
$lnk.Description      = "BRIDGE Craig RPA"
$lnk.IconLocation     = "C:\Windows\System32\shell32.dll,145"
$lnk.Save()
Write-Host "OK: desktop shortcut -> $lnkPath"

# STEP 5: Verify files
$ok = $true
foreach ($f in @($VBS, "$BASE\launcher.pyw", "$BASE\craigslist_auto_rpa.py", "$BASE\rpa_overlay.py", $PYTHONW)) {
    if (Test-Path $f) { Write-Host "OK: $f" }
    else              { Write-Host "MISSING: $f"; $ok = $false }
}

if ($ok) { Write-Host "`nALL DONE - RPA restored successfully" }
else     { Write-Host "`nWARN: Some files missing - check above" }
