# Adobe 업데이트/모니터링 서비스 완전 비활성화 스크립트
# 실행: powershell -ExecutionPolicy Bypass -File adobe_disable.ps1

$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== Adobe 서비스 탐색 ===" -ForegroundColor Cyan

# 1. 서비스 목록 확인
$adobeServices = Get-WmiObject Win32_Service | Where-Object {
    $_.Name -like "*Adobe*" -or
    $_.Name -like "*AGS*" -or
    $_.Name -like "*ARM*" -or
    $_.DisplayName -like "*Adobe*" -or
    $_.DisplayName -like "*Genuine*"
}

Write-Host "`n발견된 Adobe 서비스:"
foreach ($svc in $adobeServices) {
    Write-Host "  - $($svc.Name) | $($svc.DisplayName) | $($svc.State) | $($svc.StartMode)"
}

if ($adobeServices.Count -eq 0) {
    Write-Host "  (없음)" -ForegroundColor Yellow
}

# 2. 예약 작업 확인
Write-Host "`n=== Adobe 예약 작업 ===" -ForegroundColor Cyan
$adobeTasks = Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object {
    $_.TaskName -like "*Adobe*" -or
    $_.TaskPath -like "*Adobe*"
}

Write-Host "발견된 Adobe 예약 작업:"
foreach ($task in $adobeTasks) {
    Write-Host "  - $($task.TaskPath)$($task.TaskName) | $($task.State)"
}

if ($adobeTasks.Count -eq 0) {
    Write-Host "  (없음)" -ForegroundColor Yellow
}

# 3. AGS 전용 확인
Write-Host "`n=== AGS (Adobe Genuine Software) 탐색 ===" -ForegroundColor Cyan
$agsPaths = @(
    "C:\Program Files\Adobe\Adobe Desktop Common\NGL",
    "C:\Program Files (x86)\Common Files\Adobe",
    "C:\Program Files\Common Files\Adobe\CAI"
)
foreach ($path in $agsPaths) {
    if (Test-Path $path) {
        Write-Host "  경로 존재: $path"
        Get-ChildItem $path -Filter "*.exe" | ForEach-Object {
            Write-Host "    exe: $($_.FullName)"
        }
    }
}

# 4. 레지스트리 업데이트 설정
Write-Host "`n=== 레지스트리 업데이트 키 ===" -ForegroundColor Cyan
$regPaths = @(
    "HKLM:\SOFTWARE\Adobe",
    "HKLM:\SOFTWARE\WOW6432Node\Adobe",
    "HKCU:\SOFTWARE\Adobe"
)
foreach ($reg in $regPaths) {
    if (Test-Path $reg) {
        Write-Host "  레지스트리 존재: $reg"
    }
}

Write-Host "`n=== 탐색 완료 ===" -ForegroundColor Green
Write-Host "위 결과를 확인 후 비활성화를 진행하세요."
