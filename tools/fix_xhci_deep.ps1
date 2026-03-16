# AMD xHCI 컨트롤러 깊은 수준 수정
$ErrorActionPreference = "SilentlyContinue"

# 1. AMD xHCI 레지스트리 파라미터 수정 (USB 2.0 장치 인식 개선)
Write-Host "[1/3] xHCI 드라이버 파라미터 수정..." -ForegroundColor Cyan

$amdPCI = Get-PnpDevice | Where-Object {
    $_.InstanceId -match "PCI\\VEN_1022.*DEV_43D5|PCI\\VEN_1022.*DEV_145F"
}
foreach ($ctrl in $amdPCI) {
    $regPath = "HKLM:\SYSTEM\CurrentControlSet\Enum\$($ctrl.InstanceId)\Device Parameters"
    if (-not (Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }

    # USB 2.0 장치를 USB 3.0 포트에서 강제 인식하는 설정
    Set-ItemProperty -Path $regPath -Name "UsbDeviceResetOnResume"  -Value 1 -Type DWord
    Set-ItemProperty -Path $regPath -Name "DisableOnSoftRemove"     -Value 0 -Type DWord

    # xHCI 드라이버 파라미터 경로
    $svcPath = "HKLM:\SYSTEM\CurrentControlSet\Services\USBXHCI\Parameters"
    if (-not (Test-Path $svcPath)) { New-Item -Path $svcPath -Force | Out-Null }
    Set-ItemProperty -Path $svcPath -Name "DisableSelectiveSuspend" -Value 1 -Type DWord

    Write-Host "  OK: $($ctrl.FriendlyName) | $($ctrl.InstanceId)"
}

# usbhub3 서비스 파라미터
$hub3Path = "HKLM:\SYSTEM\CurrentControlSet\Services\usbhub3\Parameters"
if (-not (Test-Path $hub3Path)) { New-Item -Path $hub3Path -Force | Out-Null }
Set-ItemProperty -Path $hub3Path -Name "DisableSelectiveSuspend" -Value 1 -Type DWord

# USB 서비스 전체 SelectiveSuspend 비활성화
foreach ($svc in @("USB","usbhub","usbhub3","USBXHCI","usbccgp")) {
    $p = "HKLM:\SYSTEM\CurrentControlSet\Services\$svc"
    if (Test-Path $p) {
        Set-ItemProperty -Path $p -Name "DisableSelectiveSuspend" -Value 1 -Type DWord
    }
}

# 2. Windows USB 진단 수행
Write-Host "[2/3] Windows USB 스택 진단/수복..." -ForegroundColor Cyan
$dismResult = DISM /Online /Cleanup-Image /ScanHealth 2>&1 | Select-String "No component store corruption"
if ($dismResult) {
    Write-Host "  Windows 시스템 파일 정상" -ForegroundColor Green
} else {
    Write-Host "  DISM 수복 실행 중..."
    DISM /Online /Cleanup-Image /RestoreHealth 2>&1 | Out-Null
}

# 3. 전체 재스캔
Write-Host "[3/3] 장치 재스캔..." -ForegroundColor Cyan
pnputil /scan-devices 2>&1 | Out-Null
Start-Sleep -Seconds 5

# 결과
Write-Host ""
Write-Host "=== 결과 ===" -ForegroundColor Green
$n460 = Get-PnpDevice | Where-Object { $_.FriendlyName -match "N460|ABKO" -or $_.InstanceId -match "VID_0C76" }
$n460 | Select-Object Status, FriendlyName, InstanceId | Format-Table

$events = Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -MaxEvents 20 |
          Where-Object { $_.TimeCreated -gt (Get-Date).AddSeconds(-20) }
Write-Host "PnP events: $($events.Count)"

Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue
$audioN460 = Get-AudioDevice -List | Where-Object { $_.Name -match "N460|ABKO" }
if ($audioN460) {
    Write-Host "N460 detected!" -ForegroundColor Green
    $out = $audioN460 | Where-Object { $_.Type -eq "Playback"  } | Select-Object -First 1
    $mic = $audioN460 | Where-Object { $_.Type -eq "Recording" } | Select-Object -First 1
    if ($out) { Set-AudioDevice -ID $out.ID | Out-Null; Write-Host "Output: $($out.Name)" }
    if ($mic) { Set-AudioDevice -ID $mic.ID -RecordingDefault | Out-Null; Write-Host "Input: $($mic.Name)" }
} else {
    Write-Host "N460 not detected - settings applied, reboot required" -ForegroundColor Yellow
}
