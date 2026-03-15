# BRIDGE RPA Task Registration (Register-ScheduledTask, space-safe)
$ErrorActionPreference = "Continue"

$PS1     = "Q:\Claudework\bridge base\scripts\run_craigslist_rpa.ps1"
$PYTHON  = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe"
$DESKTOP = [Environment]::GetFolderPath("Desktop")
$BASE    = "Q:\Claudework\bridge base"
$VBS     = "$BASE\start_craig.vbs"

# ── Action: powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File "..."
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$PS1`"" `
    -WorkingDirectory $BASE

# ── Trigger 1: At Logon (2 min delay)
$trigLogon         = New-ScheduledTaskTrigger -AtLogOn
$trigLogon.Delay   = "PT2M"

# ── Trigger 2: Every 6 hours (starting from now)
$trigRepeat        = New-ScheduledTaskTrigger -Once -At (Get-Date) `
                        -RepetitionInterval (New-TimeSpan -Hours 6) `
                        -RepetitionDuration ([TimeSpan]::MaxValue)

# ── Settings
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
    -MultipleInstances IgnoreNew `
    -RunOnlyIfNetworkAvailable `
    -StartWhenAvailable

# ── Principal (run as current user, highest)
$principal = New-ScheduledTaskPrincipal `
    -UserId ([Environment]::UserName) `
    -LogonType Interactive `
    -RunLevel Highest

# ── Remove old tasks
Unregister-ScheduledTask -TaskName "BridgeCraigslistRPA"    -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "BridgeCraigslistRPA_6H" -Confirm:$false -ErrorAction SilentlyContinue

# ── Register new tasks
Register-ScheduledTask `
    -TaskName "BridgeCraigslistRPA" `
    -Action   $action `
    -Trigger  $trigLogon `
    -Settings $settings `
    -Principal $principal `
    -Description "BRIDGE Craigslist RPA - runs at login" `
    -Force | Out-Null

Register-ScheduledTask `
    -TaskName "BridgeCraigslistRPA_6H" `
    -Action   $action `
    -Trigger  $trigRepeat `
    -Settings $settings `
    -Principal $principal `
    -Description "BRIDGE Craigslist RPA - runs every 6 hours" `
    -Force | Out-Null

Write-Host "REGISTERED: BridgeCraigslistRPA (at logon + 2min)"
Write-Host "REGISTERED: BridgeCraigslistRPA_6H (every 6h)"

# ── Desktop shortcut
$lnkPath = "$DESKTOP\BRIDGE Craig RPA.lnk"
$ws      = New-Object -ComObject WScript.Shell
$lnk     = $ws.CreateShortcut($lnkPath)
$lnk.TargetPath       = "wscript.exe"
$lnk.Arguments        = "`"$VBS`""
$lnk.WorkingDirectory = $BASE
$lnk.Description      = "BRIDGE Craig RPA"
$lnk.IconLocation     = "Q:\Claudework\bridge base\images\craig_icon.ico,0"
$lnk.Save()
Write-Host "SHORTCUT: $lnkPath"

# ── Verify
$t1 = Get-ScheduledTask -TaskName "BridgeCraigslistRPA"    -ErrorAction SilentlyContinue
$t2 = Get-ScheduledTask -TaskName "BridgeCraigslistRPA_6H" -ErrorAction SilentlyContinue
Write-Host "VERIFY BridgeCraigslistRPA:    $(if($t1){'OK - State:'+$t1.State}else{'MISSING'})"
Write-Host "VERIFY BridgeCraigslistRPA_6H: $(if($t2){'OK - State:'+$t2.State}else{'MISSING'})"
Write-Host "SHORTCUT exists: $(Test-Path $lnkPath)"
Write-Host "DONE"
