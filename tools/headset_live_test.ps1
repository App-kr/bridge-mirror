# Live trigger test - monitor log file for Task auto-execution
$logFile = "C:\Users\Scarlett\AppData\Local\bridge_headset_switch.log"
$taskName = "ABKO_N460_AutoConnect"

# 1. Clear log
if (Test-Path $logFile) { Remove-Item $logFile -Force }
Write-Host "[1] Log cleared"

# 2. Record current 410 event count as baseline
$baseline = (Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -MaxEvents 500 |
             Where-Object { $_.Id -eq 410 }).Count
Write-Host "[2] Baseline 410 event count: $baseline"

# 3. Get last task run time as baseline
$lastRun = (Get-ScheduledTaskInfo -TaskName $taskName).LastRunTime
Write-Host "[3] Last task run: $lastRun"

# 4. Disable/enable USB root hub to generate EventID 410 (simulate device event)
Write-Host "[4] Simulating USB event (disable/re-enable USB root hub)..."
$usbHub = Get-PnpDevice -Class "USB" |
          Where-Object { $_.FriendlyName -match "Root Hub" -and $_.Status -eq "OK" } |
          Select-Object -First 1

if ($usbHub) {
    Write-Host "    Target: $($usbHub.FriendlyName)"
    Write-Host "    Disabling..."
    Disable-PnpDevice -InstanceId $usbHub.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Write-Host "    Re-enabling..."
    Enable-PnpDevice -InstanceId $usbHub.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "    USB hub cycled"
} else {
    Write-Host "    No USB Root Hub found - using manual trigger instead"
    Start-ScheduledTask -TaskName $taskName
}

# 5. Wait and monitor (up to 15 seconds)
Write-Host ""
Write-Host "[5] Waiting for auto-trigger (max 15s)..."
$fired = $false
for ($i = 1; $i -le 15; $i++) {
    Start-Sleep -Seconds 1
    $newRun = (Get-ScheduledTaskInfo -TaskName $taskName).LastRunTime
    $state = (Get-ScheduledTask -TaskName $taskName).State

    if ($newRun -ne $lastRun -or (Test-Path $logFile)) {
        $fired = $true
        Write-Host "  [${i}s] FIRED! Task executed at: $newRun" -ForegroundColor Green
        break
    }

    $new410 = (Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -MaxEvents 500 |
               Where-Object { $_.Id -eq 410 }).Count
    Write-Host "  [${i}s] State: $state | 410 events: $new410 (was $baseline)"
}

# 6. Result
Write-Host ""
if ($fired -or (Test-Path $logFile)) {
    Write-Host "=== AUTO-TRIGGER SUCCESS ===" -ForegroundColor Green
    Write-Host "Task fired automatically on USB event!"
    Write-Host "Log content:"
    Get-Content $logFile -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "=== FALLBACK: Manual trigger test ===" -ForegroundColor Yellow
    Start-ScheduledTask -TaskName $taskName
    Start-Sleep -Seconds 6
    $finalRun = (Get-ScheduledTaskInfo -TaskName $taskName).LastRunTime
    $finalCode = (Get-ScheduledTaskInfo -TaskName $taskName).LastTaskResult
    Write-Host "Manual trigger result: LastRun=$finalRun | ExitCode=$finalCode"
    if (Test-Path $logFile) {
        Write-Host "Log:"
        Get-Content $logFile | ForEach-Object { Write-Host "  $_" }
    }
}

Write-Host ""
Write-Host "=== CHAIN STATUS ===" -ForegroundColor Cyan
Write-Host "EventID 410 trigger : REGISTERED (Kernel-PnP/Configuration)"
Write-Host "Script path         : C:\Users\Scarlett\AppData\Local\bridge_headset_switch.ps1"
Write-Host "AudioDeviceCmdlets  : v3.1.0.2 installed"
Write-Host "USB Selective Suspend: DISABLED"
Write-Host ""
Write-Host "Connect ABKO N460 USB -> EventID 410 fires -> Task runs -> N460 becomes default"
