# Watch for N460 connection in real-time
Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue
$logFile = "C:\Users\Scarlett\AppData\Local\bridge_headset_switch.log"
$prevLog = if (Test-Path $logFile) { Get-Content $logFile } else { @() }

Write-Host "Watching for ABKO N460 connection... (Ctrl+C to stop)" -ForegroundColor Yellow
Write-Host "Log file: $logFile"
Write-Host ""

for ($i = 1; $i -le 40; $i++) {
    Start-Sleep -Seconds 3
    $devices = Get-AudioDevice -List -ErrorAction SilentlyContinue
    $n460 = $devices | Where-Object { $_.Name -match "N460|ABKO" }
    $default = ($devices | Where-Object { $_.Default -eq $true -and $_.Type -eq "Playback" } | Select-Object -First 1).Name

    if ($n460) {
        $isDefault = $n460[0].Default
        Write-Host "[${i}] N460 DETECTED! Default=$default | N460_is_default=$isDefault" -ForegroundColor Cyan
        if ($isDefault) {
            Write-Host "=== AUTO-SWITCH SUCCESS ===" -ForegroundColor Green
            break
        }
    } else {
        if ($i % 4 -eq 0) {
            Write-Host "[${i}] No N460. Current default: $default"
        }
    }

    # Check log file for new entries
    if (Test-Path $logFile) {
        $newLog = Get-Content $logFile
        $newEntries = $newLog | Where-Object { $_ -notin $prevLog }
        if ($newEntries) {
            Write-Host "LOG UPDATE:" -ForegroundColor Green
            $newEntries | ForEach-Object { Write-Host "  $_" -ForegroundColor Green }
            $prevLog = $newLog
        }
    }
}
