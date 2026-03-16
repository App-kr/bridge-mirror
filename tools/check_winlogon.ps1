# Check additional startup mechanisms
Write-Host "=== Winlogon Shell/Userinit ==="
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" -ErrorAction SilentlyContinue |
    Select-Object Shell, Userinit, UserEnvDll

Write-Host ""
Write-Host "=== HKCU Windows Run ==="
Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Windows" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== Active Setup (HKLM) ==="
Get-ChildItem "HKLM:\SOFTWARE\Microsoft\Active Setup\Installed Components" -ErrorAction SilentlyContinue | ForEach-Object {
    $v = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
    if ($v.StubPath -like "*wscript*" -or $v.StubPath -like "*bridge*") {
        Write-Host "Key: $($_.Name)"
        Write-Host "  StubPath: $($v.StubPath)"
    }
}

Write-Host ""
Write-Host "=== Defender Quarantine ==="
try {
    $mpcmdrun = "C:\Program Files\Windows Defender\MpCmdRun.exe"
    if (Test-Path $mpcmdrun) {
        & $mpcmdrun -Restore -ListAll 2>&1 | Select-Object -First 30
    }
} catch {
    Write-Host "Cannot read quarantine: $_"
}

Write-Host ""
Write-Host "=== Windows Defender recent threats ==="
try {
    Get-MpThreatDetection -ErrorAction SilentlyContinue |
        Sort-Object InitialDetectionTime -Descending |
        Select-Object -First 10 InitialDetectionTime, ThreatName, ActionSuccess, Resources |
        Format-Table -AutoSize -Wrap
} catch {
    Write-Host "Cannot read threat history: $_"
}
