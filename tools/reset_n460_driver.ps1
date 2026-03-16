# ABKO N460 드라이버 캐시 초기화 및 재연결 준비
Write-Host "=== STEP 1: N460 유령 장치 항목 제거 ===" -ForegroundColor Cyan

# 현재 N460 관련 모든 항목
$n460devices = Get-PnpDevice | Where-Object FriendlyName -match "N460|ABKO"
Write-Host "제거 대상 항목:"
$n460devices | Select-Object Status, FriendlyName, InstanceId | Format-Table -AutoSize

# Unknown 상태 항목 제거 (유령 드라이버)
foreach ($dev in $n460devices) {
    if ($dev.Status -eq "Unknown") {
        Write-Host "제거 중: $($dev.FriendlyName) ($($dev.InstanceId))"
        try {
            & pnputil /remove-device $dev.InstanceId 2>&1
        } catch {
            Write-Host "  skip: $_"
        }
    }
}

# USB 복합 장치도 제거
$n460usb = Get-PnpDevice -Class USB | Where-Object { $_.InstanceId -match "0C76|161F" }
foreach ($dev in $n460usb) {
    Write-Host "USB 제거 중: $($dev.InstanceId)"
    & pnputil /remove-device $dev.InstanceId 2>&1
}

Write-Host ""
Write-Host "=== STEP 2: USB 드라이버 재스캔 ===" -ForegroundColor Cyan
pnputil /scan-devices 2>&1

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "=== STEP 3: 제거 후 상태 확인 ===" -ForegroundColor Cyan
$remaining = Get-PnpDevice | Where-Object FriendlyName -match "N460|ABKO"
if ($remaining) {
    Write-Host "남은 항목:"
    $remaining | Select-Object Status, FriendlyName, InstanceId | Format-Table
} else {
    Write-Host "N460 항목 완전 제거됨" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== 완료 ===" -ForegroundColor Green
Write-Host "지금 ABKO N460 USB를 꽂아주세요 - Windows가 새 장치로 인식합니다"
