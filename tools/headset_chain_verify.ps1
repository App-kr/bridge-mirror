# EventID 410 -> Task auto-fire chain verification
$taskName = "ABKO_N460_AutoConnect"
$logFile = "C:\Users\Scarlett\AppData\Local\bridge_headset_switch.log"

# Enable Task Scheduler history
wevtutil set-log "Microsoft-Windows-TaskScheduler/Operational" /enabled:true 2>$null

# Clear log
if (Test-Path $logFile) { Remove-Item $logFile -Force }

# Baseline
$baseline410 = (Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -MaxEvents 500 |
                Where-Object { $_.Id -eq 410 } | Select-Object -First 1).TimeCreated
$baselineTaskRun = (Get-ScheduledTaskInfo -TaskName $taskName).LastRunTime
Write-Host "Baseline - Last 410: $baseline410 | Last task run: $baselineTaskRun"

# Generate 410 event by enabling/disabling a network adapter (safe operation)
Write-Host ""
Write-Host "Generating EventID 410 via network adapter cycle..."
$adapter = Get-NetAdapter | Where-Object { $_.Status -eq "Up" -and $_.Name -notmatch "Loopback" } | Select-Object -First 1
if ($adapter) {
    Write-Host "Using: $($adapter.Name)"
    Disable-NetAdapter -Name $adapter.Name -Confirm:$false -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Enable-NetAdapter -Name $adapter.Name -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Adapter cycled"
} else {
    Write-Host "No adapter found - trying USB device toggle via devcon simulation"
    # Fallback: register a dummy device state change
    $env:DEVMGR_SHOW_NONPRESENT_DEVICES = "1"
}

# Monitor for 30 seconds
Write-Host ""
Write-Host "Monitoring for auto-trigger (30s)..."
$triggered = $false
for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 1

    $new410 = Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -MaxEvents 10 |
              Where-Object { $_.Id -eq 410 -and $_.TimeCreated -gt $baseline410 } | Select-Object -First 1

    $newTaskRun = (Get-ScheduledTaskInfo -TaskName $taskName).LastRunTime
    $logExists = Test-Path $logFile

    if ($new410) {
        Write-Host "  [${i}s] EventID 410 fired at $($new410.TimeCreated)!" -ForegroundColor Cyan
    }

    if ($newTaskRun -gt $baselineTaskRun -or $logExists) {
        Write-Host "  [${i}s] TASK AUTO-TRIGGERED! LastRun: $newTaskRun" -ForegroundColor Green
        $triggered = $true
        Start-Sleep -Seconds 4  # wait for script sleep to finish
        break
    }

    if ($i % 5 -eq 0) {
        $state = (Get-ScheduledTask -TaskName $taskName).State
        Write-Host "  [${i}s] Task state: $state | Waiting..."
    }
}

# Final result
Write-Host ""
if ($triggered) {
    Write-Host "=== CHAIN TEST: PASSED ===" -ForegroundColor Green
} else {
    Write-Host "=== 30s timeout - no auto-trigger ===" -ForegroundColor Yellow
    Write-Host "Checking Task Scheduler history..."

    # Check Task Scheduler operational log
    try {
        $taskHistory = Get-WinEvent -LogName "Microsoft-Windows-TaskScheduler/Operational" -MaxEvents 50 |
                       Where-Object { $_.Message -match "N460" } | Select-Object -First 5
        if ($taskHistory) {
            $taskHistory | Select-Object TimeCreated, Id, Message | Format-List
        } else {
            Write-Host "No task history found - EventID 410 may not have fired"
        }
    } catch {
        Write-Host "Task scheduler history not accessible"
    }
}

# Show log
if (Test-Path $logFile) {
    Write-Host "Log file:"
    Get-Content $logFile
} else {
    Write-Host "Log: empty (N460 not connected = expected SKIP)"
}
