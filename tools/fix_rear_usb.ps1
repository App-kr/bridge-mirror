# Rear USB port fix for ABKO N460
$ErrorActionPreference = "SilentlyContinue"

# 1. USB Root Hub power management OFF
Write-Host "[1/4] USB Root Hub power management OFF" -ForegroundColor Cyan
$rootHubs = Get-PnpDevice -Class USB | Where-Object FriendlyName -match "Root Hub"
foreach ($hub in $rootHubs) {
    $dpPath = "HKLM:\SYSTEM\CurrentControlSet\Enum\$($hub.InstanceId)\Device Parameters"
    if (-not (Test-Path $dpPath)) { New-Item -Path $dpPath -Force | Out-Null }
    Set-ItemProperty -Path $dpPath -Name "AllowIdleIrpInD3"               -Value 0 -Type DWord
    Set-ItemProperty -Path $dpPath -Name "EnhancedPowerManagementEnabled" -Value 0 -Type DWord
    Set-ItemProperty -Path $dpPath -Name "SelectiveSuspendEnabled"        -Value 0 -Type DWord
    Write-Host "  OK: $($hub.FriendlyName)"
}

# 2. AMD/NVIDIA USB controller power management OFF
Write-Host "[2/4] AMD/NVIDIA USB controller power management OFF" -ForegroundColor Cyan
$ctrls = Get-PnpDevice | Where-Object { $_.FriendlyName -match "AMD USB|NVIDIA USB" -and $_.Status -eq "OK" }
foreach ($c in $ctrls) {
    $dpPath = "HKLM:\SYSTEM\CurrentControlSet\Enum\$($c.InstanceId)\Device Parameters"
    if (-not (Test-Path $dpPath)) { New-Item -Path $dpPath -Force | Out-Null }
    Set-ItemProperty -Path $dpPath -Name "AllowIdleIrpInD3"               -Value 0 -Type DWord
    Set-ItemProperty -Path $dpPath -Name "EnhancedPowerManagementEnabled" -Value 0 -Type DWord
    Write-Host "  OK: $($c.FriendlyName)"
}

# 3. Remove failed/ghost device entries
Write-Host "[3/4] Remove failed device entries" -ForegroundColor Cyan
Get-PnpDevice -Class USB | Where-Object { $_.InstanceId -match "VID_0000" } | ForEach-Object {
    Write-Host "  Removing: $($_.InstanceId)"
    pnputil /remove-device $_.InstanceId 2>&1 | Out-Null
}
Get-PnpDevice | Where-Object { $_.FriendlyName -match "N460|ABKO" -or $_.InstanceId -match "VID_0C76" } | ForEach-Object {
    pnputil /remove-device $_.InstanceId 2>&1 | Out-Null
}

# 4. Restart AMD xHCI controllers (force USB bus reset)
Write-Host "[4/4] Restart AMD xHCI controllers" -ForegroundColor Cyan
$amdCtrls = Get-PnpDevice | Where-Object { $_.FriendlyName -match "AMD USB 3" -and $_.Status -eq "OK" }
foreach ($c in $amdCtrls) {
    Write-Host "  Cycling: $($c.FriendlyName)"
    Disable-PnpDevice -InstanceId $c.InstanceId -Confirm:$false
    Start-Sleep -Milliseconds 1000
    Enable-PnpDevice -InstanceId $c.InstanceId -Confirm:$false
    Start-Sleep -Milliseconds 500
}

pnputil /scan-devices 2>&1 | Out-Null
Start-Sleep -Seconds 5

# Result check
Write-Host ""
Write-Host "=== Result ===" -ForegroundColor Green
$n460 = Get-PnpDevice | Where-Object { $_.FriendlyName -match "N460|ABKO" -or $_.InstanceId -match "VID_0C76" }
$n460 | Select-Object Status, FriendlyName, InstanceId | Format-Table -AutoSize

$pnpEvents = Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -MaxEvents 50 |
             Where-Object { $_.TimeCreated -gt (Get-Date).AddSeconds(-30) }
Write-Host "PnP events (last 30s): $($pnpEvents.Count)"
if ($pnpEvents.Count -gt 0) {
    $pnpEvents | Group-Object Id | Select-Object Name, Count | Format-Table -AutoSize
}

Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue
$audioN460 = Get-AudioDevice -List | Where-Object { $_.Name -match "N460|ABKO" }
if ($audioN460) {
    Write-Host "N460 audio detected - setting as default" -ForegroundColor Green
    $out = $audioN460 | Where-Object { $_.Type -eq "Playback"  } | Select-Object -First 1
    $mic = $audioN460 | Where-Object { $_.Type -eq "Recording" } | Select-Object -First 1
    if ($out) {
        Set-AudioDevice -ID $out.ID | Out-Null
        Write-Host "Default output: $($out.Name)" -ForegroundColor Green
    }
    if ($mic) {
        Set-AudioDevice -ID $mic.ID -RecordingDefault | Out-Null
        Write-Host "Default input: $($mic.Name)" -ForegroundColor Green
    }
} else {
    Write-Host "N460 still not detected in audio stack" -ForegroundColor Yellow
    Write-Host "All current audio devices:"
    Get-AudioDevice -List | Select-Object Default, Type, Name | Format-Table -AutoSize
}
