# USB 케이블/포트 데이터 통신 진단
Write-Host "=== USB 허브 포트 점유 현황 ===" -ForegroundColor Cyan

# USB 허브별 연결된 장치 확인
$usbOK = Get-PnpDevice -Class USB | Where-Object Status -eq OK
Write-Host "현재 OK 상태 USB 장치 수: $($usbOK.Count)"

# 포트 식별자 분석 - 새 포트에 N460이 있는지
$allUSB = Get-PnpDevice -Class USB
$n460Candidates = $allUSB | Where-Object { $_.InstanceId -match "0C76|161F" }
Write-Host ""
Write-Host "VID_0C76(ABKO) 관련 모든 USB 항목:"
$n460Candidates | Select-Object Status, FriendlyName, InstanceId | Format-List

# 새로 연결된 장치 감지 - 이전에 없던 항목
Write-Host "=== 현재 OK 상태 USB Composite 장치 ===" -ForegroundColor Cyan
$allUSB | Where-Object { $_.Status -eq "OK" -and $_.FriendlyName -match "Composite" } |
    Select-Object FriendlyName, InstanceId | Format-List

# USB 허브 연결 수 확인 (포트가 실제로 데이터 통신 중인지)
Write-Host "=== USB 허브 포트 데이터 통신 확인 ===" -ForegroundColor Cyan
try {
    $usbHub = Get-WmiObject -Namespace root/CIMV2 -Class Win32_USBHub -ErrorAction Stop
    foreach ($hub in $usbHub) {
        Write-Host "Hub: $($hub.DeviceID) | CurrentNumberOfPorts: $($hub.CurrentNumberOfPorts)"
    }
} catch {
    Write-Host "WMI USB Hub 쿼리 실패: $_"
}
