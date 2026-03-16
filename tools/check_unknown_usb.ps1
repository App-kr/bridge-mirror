# "장치 설명자 요청 실패" 장치 상세 확인
Write-Host "=== Unknown/Failed USB Devices ===" -ForegroundColor Red

Get-PnpDevice -Class "USB" | Where-Object { $_.Status -ne "OK" } |
    Select-Object Status, FriendlyName, InstanceId | Format-List

Write-Host "=== Device Error Codes ===" -ForegroundColor Cyan

# ConfigManagerErrorCode 확인 (43 = 장치 설명자 요청 실패)
Get-WmiObject Win32_USBControllerDevice | ForEach-Object {
    $dep = [wmi]($_.Dependent)
    if ($dep.ConfigManagerErrorCode -ne 0) {
        Write-Host "ERROR [$($dep.ConfigManagerErrorCode)]: $($dep.Name) | $($dep.DeviceID)"
    }
}

# 직접 확인
$unknownDev = Get-PnpDevice | Where-Object {
    $_.FriendlyName -match "실패|Unknown|설명자" -or
    ($_.Status -eq "Unknown" -and $_.Class -eq "USB")
}
Write-Host ""
Write-Host "=== Problematic USB device details ===" -ForegroundColor Yellow
$unknownDev | Select-Object Status, FriendlyName, InstanceId | Format-List
