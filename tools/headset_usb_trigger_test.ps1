# USB 장치 비활성/활성화로 EventID 410 발생 → Task 자동 실행 검증
$taskName = "ABKO_N460_AutoConnect"
$logFile = "C:\Users\Scarlett\AppData\Local\bridge_headset_switch.log"

if (Test-Path $logFile) { Remove-Item $logFile -Force }

# USB 장치 (현재 연결된 것) 확인
Write-Host "=== Available USB devices to cycle ===" -ForegroundColor Cyan
$usbDevices = Get-PnpDevice -Class "USB" | Where-Object { $_.Status -eq "OK" }
$usbDevices | Select-Object Status, FriendlyName, InstanceId | Format-Table -AutoSize

# SC03 USB Microphone 사용 (현재 OK 상태인 USB 오디오 장치)
$sc03 = Get-PnpDevice | Where-Object { $_.FriendlyName -match "SC03" -and $_.Status -eq "OK" -and $_.Class -eq "MEDIA" }
Write-Host ""
if ($sc03) {
    Write-Host "Target device for test: $($sc03.FriendlyName)" -ForegroundColor Green
    Write-Host "InstanceId: $($sc03.InstanceId)"

    $baseline = (Get-ScheduledTaskInfo -TaskName $taskName).LastRunTime
    $baseline410time = (Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -MaxEvents 10 |
                        Where-Object { $_.Id -eq 410 } | Select-Object -First 1).TimeCreated

    Write-Host ""
    Write-Host "Baseline task run: $baseline"
    Write-Host "Baseline last 410: $baseline410time"

    # Disable device
    Write-Host ""
    Write-Host "Disabling $($sc03.FriendlyName)..."
    Disable-PnpDevice -InstanceId $sc03.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2

    # Re-enable device (this should generate EventID 410)
    Write-Host "Re-enabling..."
    Enable-PnpDevice -InstanceId $sc03.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Device cycled. Monitoring for 20s..."

    # Monitor
    $fired = $false
    for ($i = 1; $i -le 20; $i++) {
        Start-Sleep -Seconds 1
        $new410 = Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -MaxEvents 5 |
                  Where-Object { $_.Id -eq 410 -and $_.TimeCreated -gt $baseline410time } | Select-Object -First 1
        $newRun = (Get-ScheduledTaskInfo -TaskName $taskName).LastRunTime

        if ($new410) {
            Write-Host "  [${i}s] EventID 410 generated! Time: $($new410.TimeCreated)" -ForegroundColor Cyan
        }
        if ($newRun -gt $baseline -or (Test-Path $logFile)) {
            Write-Host "  [${i}s] TASK FIRED! Run time: $newRun" -ForegroundColor Green
            $fired = $true
            Start-Sleep -Seconds 4
            break
        }
        if ($i % 5 -eq 0) { Write-Host "  [${i}s] Waiting... Task: $((Get-ScheduledTask -TaskName $taskName).State)" }
    }

    Write-Host ""
    if ($fired) {
        Write-Host "=== CHAIN VERIFIED: EventID 410 -> Task AUTO-FIRED ===" -ForegroundColor Green
    } else {
        Write-Host "=== Chain not verified - checking event count ===" -ForegroundColor Yellow
        $after410 = (Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -MaxEvents 10 |
                     Where-Object { $_.Id -eq 410 } | Select-Object -First 1).TimeCreated
        Write-Host "Latest 410 after cycle: $after410 (was $baseline410time)"
        if ($after410 -gt $baseline410time) {
            Write-Host "410 DID fire but Task delay may be longer than 20s" -ForegroundColor Yellow
        } else {
            Write-Host "410 did NOT fire from device disable/enable" -ForegroundColor Red
        }
    }
} else {
    Write-Host "SC03 not found in OK state - checking all OK USB devices..." -ForegroundColor Yellow
    $usbDevices | Select-Object Status, FriendlyName | Format-Table -AutoSize
}

if (Test-Path $logFile) {
    Write-Host "Log:"
    Get-Content $logFile
}
