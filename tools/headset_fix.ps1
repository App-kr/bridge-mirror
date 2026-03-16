# ABKO N460 헤드셋 자동연결 수정 스크립트
# 실행: powershell -ExecutionPolicy Bypass -File headset_fix.ps1

# ============================================================
# FIX 1: USB Selective Suspend 비활성화 (전원 계획 설정)
# ============================================================
Write-Host "[FIX 1] USB Selective Suspend 비활성화 중..." -ForegroundColor Cyan

# 현재 활성 전원 계획 GUID 가져오기
$activePlan = (powercfg /getactivescheme) -replace '.*GUID: ([a-f0-9-]+).*', '$1'
Write-Host "  활성 전원 계획: $activePlan"

# USB Selective Suspend 비활성화 (AC 및 배터리 모두)
# GUID: 2a737441-1930-4402-8d77-b2bebba308a3 = USB Settings
# GUID: d4e98f31-5ffe-4ce1-be31-1b38b384c009 = USB Selective Suspend
powercfg /setacvalueindex $activePlan 2a737441-1930-4402-8d77-b2bebba308a3 d4e98f31-5ffe-4ce1-be31-1b38b384c009 0
powercfg /setdcvalueindex $activePlan 2a737441-1930-4402-8d77-b2bebba308a3 d4e98f31-5ffe-4ce1-be31-1b38b384c009 0
powercfg /setactive $activePlan

Write-Host "  [OK] USB Selective Suspend 비활성화 완료" -ForegroundColor Green

# ============================================================
# FIX 2: 기본 오디오 장치 자동 전환 스크립트 생성
# ============================================================
Write-Host "`n[FIX 2] 자동 전환 스크립트 생성 중..." -ForegroundColor Cyan

# AudioDeviceCmdlets 모듈 확인
$hasModule = Get-Module -ListAvailable -Name "AudioDeviceCmdlets" -ErrorAction SilentlyContinue
if (-not $hasModule) {
    Write-Host "  AudioDeviceCmdlets 설치 중..." -ForegroundColor Yellow
    try {
        Install-Module -Name AudioDeviceCmdlets -Force -Scope CurrentUser -ErrorAction Stop
        Write-Host "  [OK] 모듈 설치 완료" -ForegroundColor Green
    } catch {
        Write-Host "  [SKIP] 모듈 설치 실패 - NirCmd 방식 사용" -ForegroundColor Yellow
    }
}

# 자동 전환 스크립트 작성
$switchScript = @'
# ABKO N460 기본 장치 자동 설정 스크립트
# Task Scheduler에서 USB 연결 이벤트 시 실행

Start-Sleep -Seconds 3  # 장치 초기화 대기

# AudioDeviceCmdlets 사용 시도
try {
    Import-Module AudioDeviceCmdlets -ErrorAction Stop
    $n460 = Get-AudioDevice -List | Where-Object { $_.Name -match "N460|ABKO" }
    if ($n460) {
        Set-AudioDevice -ID $n460[0].ID
        Write-Host "ABKO N460 기본 장치로 설정 완료: $($n460[0].Name)"
    }
} catch {
    # 대안: mmsys.cpl 을 통한 방법 또는 레지스트리 직접 수정
    # SoundVolumeView (NirSoft) 사용 - 없으면 알림만
    $svcPath = "C:\Tools\SoundVolumeView.exe"
    if (Test-Path $svcPath) {
        & $svcPath /SetDefault "ABKO N460" all
    } else {
        Write-Host "자동 전환 모듈 없음 - 수동 설정 필요"
    }
}
'@

$switchScriptPath = "$env:USERPROFILE\AppData\Local\bridge_headset_switch.ps1"
$switchScript | Out-File -FilePath $switchScriptPath -Encoding UTF8
Write-Host "  자동 전환 스크립트 저장: $switchScriptPath" -ForegroundColor Green

# ============================================================
# FIX 3: Task Scheduler 등록 (USB 연결 이벤트 트리거)
# ============================================================
Write-Host "`n[FIX 3] Task Scheduler 등록 중..." -ForegroundColor Cyan

$taskName = "ABKO_N460_AutoConnect"

# 기존 작업 제거
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# 트리거: USB 오디오 장치 연결 이벤트 (Event ID 0, Kernel-PnP)
# 또는 System 로그 Event ID 20001 (장치 설치됨)
$trigger = New-ScheduledTaskTrigger -AtLogOn

# 더 정확한 이벤트 기반 트리거 생성 (USB 장치 연결 = EventID 2003, PnP)
$taskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>ABKO N460 헤드셋 USB 연결 시 기본 장치로 자동 설정</Description>
  </RegistrationInfo>
  <Triggers>
    <EventTrigger>
      <Enabled>true</Enabled>
      <Subscription><![CDATA[<QueryList><Query Id="0" Path="System"><Select Path="System">*[System[Provider[@Name='Microsoft-Windows-UserPnp'] and EventID=20001]]</Select></Query></QueryList>]]></Subscription>
    </EventTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$env:USERNAME</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT1M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-WindowStyle Hidden -ExecutionPolicy Bypass -File "$switchScriptPath"</Arguments>
    </Exec>
  </Actions>
</Task>
"@

$taskXmlPath = "$env:TEMP\n460_task.xml"
$taskXml | Out-File -FilePath $taskXmlPath -Encoding Unicode

try {
    Register-ScheduledTask -TaskName $taskName -Xml (Get-Content $taskXmlPath -Raw) -Force | Out-Null
    Write-Host "  [OK] Task Scheduler 등록: $taskName" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Task Scheduler 등록 실패: $_" -ForegroundColor Yellow
    Write-Host "  수동으로 실행하세요: powershell -File $switchScriptPath" -ForegroundColor Yellow
}

# ============================================================
# FIX 4: USB 장치 전원 관리 직접 수정 (허용 시)
# ============================================================
Write-Host "`n[FIX 4] ABKO N460 USB 전원 관리 설정..." -ForegroundColor Cyan

# 레지스트리에서 ABKO N460 USB 허브 전원 관리 수정
$usbDevices = Get-PnpDevice -Class USB | Where-Object { $_.Status -eq "OK" }
foreach ($dev in $usbDevices) {
    $devKey = "HKLM:\SYSTEM\CurrentControlSet\Enum\" + $dev.InstanceId + "\Device Parameters"
    if (Test-Path $devKey) {
        $allowSuspend = (Get-ItemProperty $devKey -ErrorAction SilentlyContinue).AllowIdleIrpInD3
        if ($allowSuspend -eq $null) { continue }
    }
}

# ABKO N460 특정 USB 인스턴스 전원 관리 레지스트리 수정
$n460InstanceBase = "USB\VID_0C76&PID_161F"
$regEnum = "HKLM:\SYSTEM\CurrentControlSet\Enum"
$n460Key = Get-ChildItem -Path "$regEnum\USB" -ErrorAction SilentlyContinue |
    Where-Object { $_.PSChildName -match "VID_0C76.*PID_161F" }

if ($n460Key) {
    foreach ($key in $n460Key) {
        $instances = Get-ChildItem -Path $key.PSPath -ErrorAction SilentlyContinue
        foreach ($inst in $instances) {
            $devParams = "$($inst.PSPath)\Device Parameters"
            if (Test-Path $devParams) {
                # AllowIdleIrpInD3 = 0 → 절전 비활성화
                Set-ItemProperty -Path $devParams -Name "AllowIdleIrpInD3" -Value 0 -Type DWord -ErrorAction SilentlyContinue
                Write-Host "  [OK] 전원 관리 수정: $($inst.PSChildName)" -ForegroundColor Green
            }
        }
    }
} else {
    Write-Host "  [INFO] ABKO N460 레지스트리 항목 없음 (미연결 상태)" -ForegroundColor Gray
    Write-Host "  → 헤드셋 연결 후 재실행 필요" -ForegroundColor Yellow
}

# ============================================================
# 결과 요약
# ============================================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "수정 완료 요약:" -ForegroundColor Green
Write-Host "  1. USB Selective Suspend 비활성화 [OK]"
Write-Host "  2. 자동 전환 스크립트 생성: $switchScriptPath"
Write-Host "  3. Task Scheduler 등록 (USB 연결 이벤트 트리거)"
Write-Host "  4. USB 전원 관리 레지스트리 수정 (연결 상태 시 유효)"
Write-Host ""
Write-Host "다음 단계:" -ForegroundColor Yellow
Write-Host "  → ABKO N460 연결 후 자동 기본 장치 전환 확인"
Write-Host "  → 안 되면: powershell -File $switchScriptPath 수동 실행"
Write-Host "========================================" -ForegroundColor Cyan
