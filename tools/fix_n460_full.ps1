# N460 완전 복구 - 사용자 조작 없이 소프트웨어로 처리
$ErrorActionPreference = "SilentlyContinue"

# STEP 1: 유령 드라이버 항목 전부 제거
Write-Host "[1/5] N460 기존 드라이버 항목 제거..." -ForegroundColor Cyan
$ghosts = Get-PnpDevice | Where-Object {
    $_.FriendlyName -match "N460|ABKO" -or $_.InstanceId -match "0C76.*161F|161F.*0C76"
}
foreach ($g in $ghosts) {
    pnputil /remove-device $g.InstanceId 2>&1 | Out-Null
}

# STEP 2: USB 오디오 드라이버 캐시 초기화
Write-Host "[2/5] USB 오디오 드라이버 재설치..." -ForegroundColor Cyan
$infFiles = Get-ChildItem "C:\Windows\INF" -Filter "*.inf" |
    Select-String "VID_0C76" -List | Select-Object -ExpandProperty Filename
foreach ($inf in $infFiles) {
    pnputil /add-driver "C:\Windows\INF\$inf" /install 2>&1 | Out-Null
}
pnputil /add-driver "C:\Windows\INF\wdma_usb.inf" /install 2>&1 | Out-Null

# STEP 3: USB 선택적 일시중단 레지스트리 강제 비활성화
Write-Host "[3/5] USB 전원관리 레지스트리 강제 적용..." -ForegroundColor Cyan
$usbRegPaths = @(
    "HKLM:\SYSTEM\CurrentControlSet\Services\USB",
    "HKLM:\SYSTEM\CurrentControlSet\Services\usbhub",
    "HKLM:\SYSTEM\CurrentControlSet\Services\USBXHCI"
)
foreach ($path in $usbRegPaths) {
    if (Test-Path $path) {
        Set-ItemProperty -Path $path -Name "DisableSelectiveSuspend" -Value 1 -Type DWord -ErrorAction SilentlyContinue
    }
}

# STEP 4: USB Root Hub 전원 관리 - AllowIdleIrpInD3 전부 0으로
Write-Host "[4/5] USB 허브 전원 관리 비활성화..." -ForegroundColor Cyan
$enumPath = "HKLM:\SYSTEM\CurrentControlSet\Enum\USB"
Get-ChildItem $enumPath -ErrorAction SilentlyContinue | ForEach-Object {
    Get-ChildItem $_.PSPath -ErrorAction SilentlyContinue | ForEach-Object {
        $dp = "$($_.PSPath)\Device Parameters"
        if (Test-Path $dp) {
            Set-ItemProperty -Path $dp -Name "AllowIdleIrpInD3" -Value 0 -Type DWord -ErrorAction SilentlyContinue
            Set-ItemProperty -Path $dp -Name "EnhancedPowerManagementEnabled" -Value 0 -Type DWord -ErrorAction SilentlyContinue
            Set-ItemProperty -Path $dp -Name "SelectiveSuspendEnabled" -Value 0 -Type DWord -ErrorAction SilentlyContinue
        }
    }
}

# STEP 5: 하드웨어 변경 스캔 - Windows가 현재 연결된 장치 재감지
Write-Host "[5/5] 하드웨어 재스캔..." -ForegroundColor Cyan
pnputil /scan-devices 2>&1 | Out-Null
Start-Sleep -Seconds 5

# 결과 확인
Write-Host ""
Write-Host "=== 결과 ===" -ForegroundColor Green
$n460 = Get-PnpDevice | Where-Object { $_.FriendlyName -match "N460|ABKO" }
$n460 | Select-Object Status, FriendlyName | Format-Table -AutoSize

Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue
$audioN460 = Get-AudioDevice -List | Where-Object { $_.Name -match "N460|ABKO" }
if ($audioN460) {
    Write-Host "N460 오디오 장치 감지됨!" -ForegroundColor Green
    $audioN460 | Format-Table -AutoSize

    # 즉시 기본 장치로 설정
    $out = $audioN460 | Where-Object { $_.Type -eq "Playback" } | Select-Object -First 1
    $in  = $audioN460 | Where-Object { $_.Type -eq "Recording" } | Select-Object -First 1
    if ($out) { Set-AudioDevice -ID $out.ID | Out-Null; Write-Host "기본 출력: $($out.Name)" -ForegroundColor Green }
    if ($in)  { Set-AudioDevice -ID $in.ID -RecordingDefault | Out-Null; Write-Host "기본 입력: $($in.Name)" -ForegroundColor Green }
} else {
    Write-Host "N460 오디오 장치 미감지 - USB 드라이버 문제" -ForegroundColor Yellow

    # 남은 N460 항목 확인
    $remaining = Get-PnpDevice | Where-Object { $_.FriendlyName -match "N460|ABKO" -or $_.InstanceId -match "0C76" }
    if ($remaining) {
        Write-Host "PnP 항목:"
        $remaining | Select-Object Status, FriendlyName, InstanceId | Format-Table
    }
    Write-Host "USB Driver Status:"
    Get-PnpDevice -Class USB | Where-Object { $_.InstanceId -match "0C76" } | Select-Object Status, FriendlyName, InstanceId | Format-List
}
