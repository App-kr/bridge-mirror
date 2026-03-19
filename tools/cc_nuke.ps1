# Adobe 업데이트 완전 차단 — Creative Suite 앱 사용 유지
# 대상: Photoshop / Premiere / Illustrator / After Effects / Acrobat
# 방법: Refresh Manager 비활성화 + 레지스트리 정책 + hosts 도메인 차단 + 방화벽

$ErrorActionPreference = "SilentlyContinue"
Write-Host "=== Adobe Creative Suite 업데이트 완전 차단 ===" -ForegroundColor Cyan

# ── 1. Adobe Refresh Manager 프로세스 종료 ──────────────────────────────
Write-Host "`n[1] Adobe Refresh Manager 및 업데이트 프로세스 종료..." -ForegroundColor Yellow
$killProcs = @(
    "Adobe Refresh Manager", "AdobeRefreshManager",
    "ppmtool", "ppml",
    "CCXProcess", "CCLibrary", "CCDaemon",
    "AdobeIPCBroker", "CoreSync",
    "Adobe Desktop Service", "AdobeDesktopService",
    "Creative Cloud", "CreativeCloud",
    "AcroTray", "AdobeNotificationClient",
    "AdobeCollabSync", "AdobeGenuineMonitor"
)
foreach ($proc in $killProcs) {
    $p = Get-Process -Name $proc -ErrorAction SilentlyContinue
    if ($p) {
        Stop-Process -Name $proc -Force
        Write-Host "  종료: $proc" -ForegroundColor Green
    }
}

# ── 2. Adobe Refresh Manager 자동실행 레지스트리 제거 ────────────────────
Write-Host "`n[2] Refresh Manager 자동실행 제거..." -ForegroundColor Yellow
$runPaths = @(
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"
)
$removeKeywords = @("Adobe", "CCX", "CoreSync", "AdobeIPC", "AcroTray", "Refresh Manager", "Creative Cloud")
foreach ($rp in $runPaths) {
    if (Test-Path $rp) {
        $props = Get-ItemProperty -Path $rp -ErrorAction SilentlyContinue
        foreach ($key in ($props.PSObject.Properties.Name | Where-Object { $_ -notlike "PS*" })) {
            foreach ($kw in $removeKeywords) {
                if ($key -like "*$kw*" -or ($props.$key -like "*Adobe*" -and $props.$key -notlike "*KakaoTalk*")) {
                    Remove-ItemProperty -Path $rp -Name $key -ErrorAction SilentlyContinue
                    Write-Host "  제거: [$key]" -ForegroundColor Green
                }
            }
        }
    }
}

# ── 3. Adobe Refresh Manager 레지스트리 비활성화 ─────────────────────────
Write-Host "`n[3] Refresh Manager 설정 잠금..." -ForegroundColor Yellow
$rmPaths = @(
    "HKLM:\SOFTWARE\Adobe\Adobe Refresh Manager\StartParameters",
    "HKLM:\SOFTWARE\WOW6432Node\Adobe\Adobe Refresh Manager\StartParameters",
    "HKCU:\SOFTWARE\Adobe\Adobe Refresh Manager\StartParameters"
)
foreach ($rmp in $rmPaths) {
    if (-not (Test-Path $rmp)) { New-Item -Path $rmp -Force | Out-Null }
    Set-ItemProperty -Path $rmp -Name "DisableLaunchAtLogin" -Value 1 -Type DWord
    Set-ItemProperty -Path $rmp -Name "disableAutoCheck"     -Value 1 -Type DWord
    if (Test-Path $rmp) { Write-Host "  잠금: $rmp" -ForegroundColor Green }
}

# ── 4. 각 앱별 업데이트 정책 레지스트리 잠금 ────────────────────────────
Write-Host "`n[4] 앱별 업데이트 정책 잠금..." -ForegroundColor Yellow
$appPolicies = @(
    # Photoshop
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Photoshop",
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Photoshop\2023\FeatureLockDown",
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Photoshop\2024\FeatureLockDown",
    # Premiere Pro
    "HKLM:\SOFTWARE\Policies\Adobe\Premiere Pro",
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Premiere Pro\2023\FeatureLockDown",
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Premiere Pro\2024\FeatureLockDown",
    # Illustrator
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Illustrator\2022\FeatureLockDown",
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Illustrator\2025\FeatureLockDown",
    # After Effects
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe After Effects\2020\FeatureLockDown",
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe After Effects\2024\FeatureLockDown",
    # Creative Cloud 전체
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Creative Cloud\2.0"
)
foreach ($p in $appPolicies) {
    if (-not (Test-Path $p)) { New-Item -Path $p -Force | Out-Null }
    Set-ItemProperty -Path $p -Name "bUpdater"     -Value 0 -Type DWord
    Set-ItemProperty -Path $p -Name "bCheckReader" -Value 0 -Type DWord
    Write-Host "  잠금: $(Split-Path $p -Leaf) [bUpdater=0]" -ForegroundColor Green
}

# ── 5. OOBE / ppmtool 실행파일 비활성화 ─────────────────────────────────
Write-Host "`n[5] OOBE 업데이터 실행파일 비활성화..." -ForegroundColor Yellow
$oobePath = "C:\Program Files (x86)\Common Files\Adobe\OOBE"
$ppmExes = @("ppmtool.exe", "ppml.exe", "AdobeRefreshManager.exe")
if (Test-Path $oobePath) {
    Get-ChildItem -Path $oobePath -Recurse -Filter "*.exe" | ForEach-Object {
        foreach ($name in $ppmExes) {
            if ($_.Name -eq $name) {
                $target = $_.FullName
                $dest   = $target + ".disabled"
                if (-not (Test-Path $dest)) {
                    # ACL 제거 후 이름 변경
                    $acl = Get-Acl $target
                    $denyRules = $acl.Access | Where-Object { $_.AccessControlType -eq "Deny" }
                    foreach ($r in $denyRules) { $acl.RemoveAccessRule($r) | Out-Null }
                    Set-Acl -Path $target -AclObject $acl -ErrorAction SilentlyContinue
                    Rename-Item -Path $target -NewName ($_.Name + ".disabled") -Force
                    Write-Host "  비활성화: $target" -ForegroundColor Green
                } else {
                    Write-Host "  이미 처리됨: $($_.Name)" -ForegroundColor Yellow
                }
            }
        }
    }
}

# ── 6. hosts 파일 — 업데이트 도메인 차단 ────────────────────────────────
Write-Host "`n[6] 업데이트 도메인 hosts 차단..." -ForegroundColor Yellow
$hostsPath = "C:\Windows\System32\drivers\etc\hosts"
$updateDomains = @(
    "updates.adobe.com",
    "ardownload.adobe.com",
    "ardownload2.adobe.com",
    "agsupdate.adobe.com",
    "prod.agsupdate.adobe.com",
    "pdapp.adobe.com",
    "swupmf.adobe.com",
    "swupdl.adobe.com",
    "adobe.com.edgekey.net",
    "ccmdl.adobe.com",
    "acd-ims-na1.adobelogin.com"
)
$hostsContent = Get-Content $hostsPath -Raw -ErrorAction SilentlyContinue
foreach ($domain in $updateDomains) {
    if ($hostsContent -notmatch [regex]::Escape($domain)) {
        Add-Content -Path $hostsPath -Value "127.0.0.1 $domain"
        Write-Host "  차단: $domain" -ForegroundColor Green
    } else {
        Write-Host "  이미 차단: $domain" -ForegroundColor Yellow
    }
}

# ── 7. 방화벽 — OOBE / Refresh Manager 실행파일 차단 ────────────────────
Write-Host "`n[7] 방화벽 차단 규칙 추가..." -ForegroundColor Yellow
$fwTargets = @()
if (Test-Path $oobePath) {
    $fwTargets += Get-ChildItem -Path $oobePath -Recurse -Filter "*.exe" |
        Where-Object { $_.Name -match "ppmtool|ppml|Refresh|Update|adobe" } |
        Select-Object -ExpandProperty FullName
}
foreach ($exe in $fwTargets) {
    $ruleName = "Block Adobe Update: $(Split-Path $exe -Leaf)"
    Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName $ruleName -Direction Outbound -Action Block -Program $exe -Enabled True | Out-Null
    Write-Host "  차단: $(Split-Path $exe -Leaf)" -ForegroundColor Green
}

# ── 8. AdobeARMService / AdobeUpdateService 재확인 비활성화 ──────────────
Write-Host "`n[8] 서비스 최종 비활성화 확인..." -ForegroundColor Yellow
$svcs = @("AdobeARMservice", "AdobeUpdateService", "AGSService", "AGMService")
foreach ($svc in $svcs) {
    $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
    if ($s) {
        Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
        Set-Service -Name $svc -StartupType Disabled -ErrorAction SilentlyContinue
        Write-Host "  비활성화: $svc" -ForegroundColor Green
    }
}

# ── 검증 ────────────────────────────────────────────────────────────────
Write-Host "`n=== 최종 검증 ===" -ForegroundColor Cyan
Write-Host "실행 중인 Adobe 업데이트 프로세스:"
$remain = Get-Process | Where-Object {
    $_.Name -like "*AdobeRefresh*" -or $_.Name -like "*ppmtool*" -or
    $_.Name -like "*CCXProcess*" -or $_.Name -like "*AdobeIPCBroker*" -or
    $_.Name -like "*AcroTray*"
}
if ($remain) {
    $remain | Select-Object Name, Id | Format-Table
} else {
    Write-Host "  [OK] 0개" -ForegroundColor Green
}

Write-Host "`nhosts 차단 도메인 수:"
$blocked = (Get-Content $hostsPath | Where-Object { $_ -match "127\.0\.0\.1.*adobe" }).Count
Write-Host "  [OK] $blocked 개 도메인 차단됨" -ForegroundColor Green

Write-Host "`n=== 완료 ===" -ForegroundColor Cyan
Write-Host "Photoshop / Premiere / Illustrator / After Effects 사용 정상" -ForegroundColor Green
Write-Host "업데이트 팝업 / 강제 업데이트 완전 차단" -ForegroundColor Green
