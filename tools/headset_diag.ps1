# ABKO N460 헤드셋 자동연결 진단 스크립트
Write-Host "=== ABKO N460 연결 현황 ===" -ForegroundColor Cyan

# 1. USB 장치 상태
$n460 = Get-PnpDevice | Where-Object { $_.FriendlyName -match "N460|ABKO" }
Write-Host "[USB 장치] ABKO N460 현재 상태:"
$n460 | Select-Object Status, FriendlyName, InstanceId | Format-List

# 2. USB 선택적 일시중단 설정
$usbKey = Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\USB" -ErrorAction SilentlyContinue
$suspendDisabled = $usbKey.DisableSelectiveSuspend
Write-Host "[전원관리] USB SelectiveSuspend 비활성화 여부: $suspendDisabled"
if ($suspendDisabled -ne 1) {
    Write-Host "  ⚠️  USB Selective Suspend 활성화됨 → 자동 절전으로 연결 해제 가능" -ForegroundColor Yellow
} else {
    Write-Host "  ✅ USB Selective Suspend 비활성화됨" -ForegroundColor Green
}

# 3. 오디오 서비스 상태
Write-Host "`n=== 오디오 관련 서비스 ===" -ForegroundColor Cyan
$services = @("AudioSrv", "AudioEndpointBuilder", "Audiosrv")
foreach ($svc in $services) {
    $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
    if ($s) {
        $color = if ($s.Status -eq "Running") { "Green" } else { "Red" }
        Write-Host ("  [{0}] {1} - StartType: {2}" -f $s.Status, $s.DisplayName, $s.StartType) -ForegroundColor $color
    }
}

# 4. 현재 기본 오디오 장치 확인 (레지스트리)
Write-Host "`n=== 기본 오디오 장치 ===" -ForegroundColor Cyan
$audioRender = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render"
if (Test-Path $audioRender) {
    Get-ChildItem $audioRender | ForEach-Object {
        $props = Get-ItemProperty -Path $_.PSPath -ErrorAction SilentlyContinue
        if ($props.DeviceState -eq 1) {  # 1 = Active
            Write-Host "  ✅ 활성 장치 ID: $($_.PSChildName)" -ForegroundColor Green
        }
    }
}

# 5. USB 루트 허브 전원 관리
Write-Host "`n=== USB 허브 전원 관리 ===" -ForegroundColor Cyan
$usbHubs = Get-PnpDevice -Class USB | Where-Object { $_.FriendlyName -match "Root Hub|Generic Hub" }
$usbHubs | Select-Object Status, FriendlyName | Format-Table -AutoSize

# 6. 이벤트 로그 - 최근 USB 연결/해제
Write-Host "`n=== 최근 USB 장치 이벤트 (Device Event Log) ===" -ForegroundColor Cyan
try {
    $events = Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -MaxEvents 200 -ErrorAction Stop
    $n460Events = $events | Where-Object { $_.Message -match "N460|VID_0C76|0C76.*161F" } | Select-Object -First 5
    if ($n460Events) {
        $n460Events | Select-Object TimeCreated, Id, Message | Format-List
    } else {
        Write-Host "  최근 ABKO N460 PnP 이벤트 없음 (현재 미연결 상태)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  이벤트 로그 접근 불가: $_" -ForegroundColor Gray
}

Write-Host "`n=== 진단 완료 ===" -ForegroundColor Cyan
