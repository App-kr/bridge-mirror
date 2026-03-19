# Adobe 업데이트/팝업 완전 차단 (Acrobat 사용은 유지)
# 서비스/프로세스는 이미 이전 스크립트로 처리됨
# 이 스크립트: 레지스트리 정책 추가 잠금

$ErrorActionPreference = "SilentlyContinue"
Write-Host "=== Adobe 업데이트/팝업 레지스트리 잠금 ===" -ForegroundColor Cyan

# ── 1. Acrobat DC (Pro) 업데이트 정책 잠금 ──────────────────────────────
$acroPolicyPath = "HKLM:\SOFTWARE\Policies\Adobe\Adobe Acrobat\DC\FeatureLockDown"
if (-not (Test-Path $acroPolicyPath)) {
    New-Item -Path $acroPolicyPath -Force | Out-Null
}
Set-ItemProperty -Path $acroPolicyPath -Name "bUpdater"        -Value 0 -Type DWord
Set-ItemProperty -Path $acroPolicyPath -Name "bCheckReader"    -Value 0 -Type DWord
Write-Host "  [OK] Acrobat DC Pro 업데이터 정책 비활성화" -ForegroundColor Green

# ── 2. Acrobat Reader DC 업데이트 정책 잠금 ──────────────────────────────
$readerPolicyPath = "HKLM:\SOFTWARE\Policies\Adobe\Acrobat Reader\DC\FeatureLockDown"
if (-not (Test-Path $readerPolicyPath)) {
    New-Item -Path $readerPolicyPath -Force | Out-Null
}
Set-ItemProperty -Path $readerPolicyPath -Name "bUpdater"      -Value 0 -Type DWord
Set-ItemProperty -Path $readerPolicyPath -Name "bCheckReader"  -Value 0 -Type DWord
Write-Host "  [OK] Acrobat Reader DC 업데이터 정책 비활성화" -ForegroundColor Green

# ── 3. Acrobat DC Installer 레지스트리 업데이트 비활성화 ─────────────────
$installerPaths = @(
    "HKLM:\SOFTWARE\Adobe\Adobe Acrobat\DC\Installer",
    "HKLM:\SOFTWARE\WOW6432Node\Adobe\Adobe Acrobat\DC\Installer",
    "HKLM:\SOFTWARE\Adobe\Acrobat Reader\DC\Installer",
    "HKLM:\SOFTWARE\WOW6432Node\Adobe\Acrobat Reader\DC\Installer"
)
foreach ($p in $installerPaths) {
    if (Test-Path $p) {
        Set-ItemProperty -Path $p -Name "DisableMaintenance" -Value 1 -Type DWord
        Set-ItemProperty -Path $p -Name "RebootRequired"     -Value 0 -Type DWord
        Write-Host "  [OK] $p" -ForegroundColor Green
    }
}

# ── 4. 업데이트 알림 사용자 레지스트리 비활성화 ─────────────────────────
$hkcuPaths = @(
    "HKCU:\SOFTWARE\Adobe\Adobe Acrobat\DC\AVAlert\cCheckBox",
    "HKCU:\SOFTWARE\Adobe\Acrobat Reader\DC\AVAlert\cCheckBox"
)
foreach ($p in $hkcuPaths) {
    if (-not (Test-Path $p)) {
        New-Item -Path $p -Force | Out-Null
    }
    # iRemindMeLaterTime=0 → 다시 알림 없음
    Set-ItemProperty -Path $p -Name "iRemindMeLaterTime" -Value 0 -Type DWord
    Write-Host "  [OK] 알림 타이머 초기화: $p" -ForegroundColor Green
}

# ── 5. Adobe Notification Manager 자동실행 제거 ─────────────────────────
$runPaths = @(
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"
)
$removeKeys = @("Adobe Acrobat", "AdobeAAMUpdater", "Adobe ARM", "AcroTray", "Adobe Reader")
foreach ($rp in $runPaths) {
    if (Test-Path $rp) {
        $props = Get-ItemProperty -Path $rp
        foreach ($key in ($props.PSObject.Properties.Name)) {
            foreach ($kw in $removeKeys) {
                if ($key -like "*$kw*") {
                    Remove-ItemProperty -Path $rp -Name $key -ErrorAction SilentlyContinue
                    Write-Host "  [OK] 자동실행 제거: $key" -ForegroundColor Green
                }
            }
        }
    }
}

# ── 6. AcroTray (시스템 트레이 알림) 프로세스 종료 ──────────────────────
$trayProcs = @("AcroTray", "AdobeCollabSync", "AdobeNotificationClient", "AdobeIPCBroker")
foreach ($proc in $trayProcs) {
    $p = Get-Process -Name $proc -ErrorAction SilentlyContinue
    if ($p) {
        Stop-Process -Name $proc -Force
        Write-Host "  [OK] 트레이 종료: $proc" -ForegroundColor Green
    }
}

# ── 검증 ────────────────────────────────────────────────────────────────
Write-Host "`n=== 검증 ===" -ForegroundColor Cyan
Write-Host "Acrobat DC Pro 정책:"
if (Test-Path $acroPolicyPath) {
    Get-ItemProperty $acroPolicyPath | Select-Object bUpdater, bCheckReader | Format-Table
}
Write-Host "Acrobat Reader 정책:"
if (Test-Path $readerPolicyPath) {
    Get-ItemProperty $readerPolicyPath | Select-Object bUpdater, bCheckReader | Format-Table
}

Write-Host "=== 완료 — Adobe 업데이트/팝업 완전 차단됨 ===" -ForegroundColor Cyan
Write-Host "Acrobat 자체는 정상 사용 가능 (업데이트만 막힘)" -ForegroundColor Green
