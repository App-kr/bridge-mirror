$ErrorActionPreference = "SilentlyContinue"
Write-Host "=== Adobe TOS Popup Suppress (Acrobat untouched) ==="

# =========================================================
# 1. EULA / TOS 수락 레지스트리 직접 설정
# =========================================================
Write-Host "`n[1] Setting TOS/EULA acceptance keys..."

$viewerHKCU = "HKCU:\SOFTWARE\Adobe\Adobe Acrobat\DC\AdobeViewer"
$viewerHKLM = "HKLM:\SOFTWARE\WOW6432Node\Adobe\Adobe Acrobat\DC\AdobeViewer"

# EULA 수락 (브라우저 포함 모든 컨텍스트)
foreach ($path in @($viewerHKCU, $viewerHKLM)) {
    if (-not (Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
    Set-ItemProperty -Path $path -Name "EULA"                  -Value 1 -Type DWord -Force
    Set-ItemProperty -Path $path -Name "EULAAcceptedForBrowser" -Value 1 -Type DWord -Force
    Set-ItemProperty -Path $path -Name "bIMSTOSAccepted"        -Value 1 -Type DWord -Force
    Set-ItemProperty -Path $path -Name "bIMSTOSPromptDisplayed" -Value 1 -Type DWord -Force
    Set-ItemProperty -Path $path -Name "bTOSCompliant"          -Value 1 -Type DWord -Force
    Write-Host "  Set: $path"
}

# IMS 레지스트리 — 서비스 권한 있음 + TOS 수락 표시
$imsPath = "HKCU:\SOFTWARE\Adobe\Adobe Acrobat\DC\IMS"
if (-not (Test-Path $imsPath)) { New-Item -Path $imsPath -Force | Out-Null }
Set-ItemProperty -Path $imsPath -Name "bIMSTOSAccepted"       -Value 1 -Type DWord -Force
Set-ItemProperty -Path $imsPath -Name "bIMSTOSShown"          -Value 1 -Type DWord -Force
Set-ItemProperty -Path $imsPath -Name "iIsUserEntitledForServices" -Value 1 -Type DWord -Force
Write-Host "  Set: $imsPath"

# =========================================================
# 2. FeatureLockDown — IMS 비활성화 (기업 정책)
#    bDisableAdobeIMS=1 → Acrobat이 IMS 서버 접속 안 함
#    → TOS 온라인 체크 자체를 우회
# =========================================================
Write-Host "`n[2] Policy: Disable IMS online check..."
$fld = "HKLM:\SOFTWARE\Policies\Adobe\Adobe Acrobat\DC\FeatureLockDown"
if (-not (Test-Path $fld)) { New-Item -Path $fld -Force | Out-Null }
Set-ItemProperty -Path $fld -Name "bDisableAdobeIMS"     -Value 1 -Type DWord -Force
Set-ItemProperty -Path $fld -Name "bIsSCCompatible"      -Value 1 -Type DWord -Force  # 기업 사이트 라이선스 플래그
Set-ItemProperty -Path $fld -Name "bAcroSuppressUpsell"  -Value 1 -Type DWord -Force  # 업셀 다이얼로그 억제
Set-ItemProperty -Path $fld -Name "bDisableTrustedFolders" -Value 0 -Type DWord -Force

# cServices 하위 키 — 온라인 서비스 연결 비활성화
$fldSvc = "$fld\cServices"
if (-not (Test-Path $fldSvc)) { New-Item -Path $fldSvc -Force | Out-Null }
Set-ItemProperty -Path $fldSvc -Name "bUpdater"              -Value 0 -Type DWord -Force
Set-ItemProperty -Path $fldSvc -Name "bToggleAdobeDocumentServices" -Value 0 -Type DWord -Force
Set-ItemProperty -Path $fldSvc -Name "bToggleAdobeSign"      -Value 0 -Type DWord -Force
Set-ItemProperty -Path $fldSvc -Name "bToggleSendAndTrack"   -Value 0 -Type DWord -Force
Set-ItemProperty -Path $fldSvc -Name "bTogglePreflightOnline" -Value 0 -Type DWord -Force
Set-ItemProperty -Path $fldSvc -Name "bToggleWebConnectors"  -Value 0 -Type DWord -Force
Write-Host "  Set: $fld"
Write-Host "  Set: $fldSvc"

# WOW6432Node 미러링
$fld32 = "HKLM:\SOFTWARE\WOW6432Node\Policies\Adobe\Adobe Acrobat\DC\FeatureLockDown"
if (-not (Test-Path $fld32)) { New-Item -Path $fld32 -Force | Out-Null }
Set-ItemProperty -Path $fld32 -Name "bDisableAdobeIMS"    -Value 1 -Type DWord -Force
Set-ItemProperty -Path $fld32 -Name "bIsSCCompatible"     -Value 1 -Type DWord -Force
Set-ItemProperty -Path $fld32 -Name "bAcroSuppressUpsell" -Value 1 -Type DWord -Force
Write-Host "  Set: $fld32"

# =========================================================
# 3. AVGeneral — TOS 관련 프롬프트 플래그
# =========================================================
Write-Host "`n[3] AVGeneral TOS flags..."
$avgen = "HKCU:\SOFTWARE\Adobe\Adobe Acrobat\DC\AVGeneral"
Set-ItemProperty -Path $avgen -Name "bIMSTOSAccepted"        -Value 1 -Type DWord -Force
Set-ItemProperty -Path $avgen -Name "bIMSTOSPromptDisplayed" -Value 1 -Type DWord -Force
Set-ItemProperty -Path $avgen -Name "bShowSignIn"            -Value 0 -Type DWord -Force
Write-Host "  Set: $avgen"

# =========================================================
# 4. adobe_licensing_wf_helper.exe 확인 및 비활성화
# =========================================================
Write-Host "`n[4] Checking adobe_licensing_wf_helper..."
$licHelper = @(
    "C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\adobe_licensing_wf_helper.exe",
    "C:\Program Files\Adobe\Acrobat DC\Acrobat\adobe_licensing_wf_helper.exe",
    "C:\Program Files (x86)\Common Files\Adobe\Adobe Desktop Common\NGL\adobe_licensing_wf_helper.exe"
)
foreach ($exe in $licHelper) {
    if (Test-Path $exe) {
        Write-Host "  FOUND: $exe"
        # 이 프로세스가 TOS 팝업을 띄울 수 있음 — 방화벽 차단
        $ruleName = "Block AdobeLicensingHelper"
        Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
        Remove-NetFirewallRule -DisplayName "$ruleName IN" -ErrorAction SilentlyContinue
        New-NetFirewallRule -DisplayName $ruleName -Direction Outbound -Action Block -Program $exe -Enabled True | Out-Null
        New-NetFirewallRule -DisplayName "$ruleName IN" -Direction Inbound -Action Block -Program $exe -Enabled True | Out-Null
        Write-Host "  Firewall blocked: $exe"
    }
}

# Acrobat 자체 방화벽 차단 (TOS 서버 연결 방지)
$acrobatExe = "C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\Acrobat.exe"
if (Test-Path $acrobatExe) {
    # 기존 규칙 있는지 확인
    $existing = Get-NetFirewallRule -DisplayName "Block Acrobat TOS" -ErrorAction SilentlyContinue
    if (-not $existing) {
        New-NetFirewallRule -DisplayName "Block Acrobat TOS" -Direction Outbound -Action Block -Program $acrobatExe -RemotePort 80,443 -Enabled True | Out-Null
        Write-Host "  Acrobat outbound 80/443 blocked (TOS check prevention)"
    } else {
        Write-Host "  Acrobat TOS firewall already exists"
    }
}

# =========================================================
# 5. Verification
# =========================================================
Write-Host "`n=== VERIFICATION ==="
Write-Host ""
Write-Host "HKCU AdobeViewer:"
Get-ItemProperty $viewerHKCU | ForEach-Object {
    $_.PSObject.Properties | Where-Object { $_.Name -match "EULA|TOS|IMS" -and $_.Name -notlike "PS*" } | ForEach-Object {
        Write-Host "  $($_.Name) = $($_.Value)"
    }
}
Write-Host ""
Write-Host "FeatureLockDown:"
Get-ItemProperty $fld | ForEach-Object {
    $_.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" } | ForEach-Object {
        Write-Host "  $($_.Name) = $($_.Value)"
    }
}

Write-Host ""
Write-Host "Done. TOS popup should no longer appear." -ForegroundColor Green
Write-Host "NOTE: Restart Acrobat once to apply changes." -ForegroundColor Yellow
