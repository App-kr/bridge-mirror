$taskName = "AdobeRegFix_Bridge"
$logFile  = "C:\Windows\Temp\adobe_reg_fix.log"
$tmpScript = "C:\Windows\Temp\adobe_reg_fix.bat"

$scriptContent = @"
@echo off
echo Starting > "$logFile"
reg query "HKLM\SOFTWARE\Adobe\Adobe ARM" >> "$logFile" 2>&1
reg add "HKLM\SOFTWARE\Adobe\Adobe ARM\Legacy" /f >> "$logFile" 2>&1
reg add "HKLM\SOFTWARE\Adobe\Adobe ARM\Legacy\Acrobat" /f >> "$logFile" 2>&1
reg add "HKLM\SOFTWARE\Adobe\Adobe ARM\Legacy\Acrobat\{AC76BA86-1033-FFFF-7760-0C0F074F4100}" /v "Check" /t REG_DWORD /d 0 /f >> "$logFile" 2>&1
echo Done >> "$logFile"
"@

[System.IO.File]::WriteAllText($tmpScript, $scriptContent, [System.Text.Encoding]::ASCII)

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action    = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$tmpScript`""
$trigger   = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(3)
$settings  = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "Task started..."
Start-Sleep -Seconds 10

# 로그 읽기
if (Test-Path $logFile) {
    Write-Host "=== Log ==="
    Get-Content $logFile
} else {
    Write-Host "Log not found - task may not have run"
}

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
