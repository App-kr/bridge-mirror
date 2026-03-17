# Windows 시스템 파일 검사 + 복구
$logPath = "Q:\Claudework\bridge base\tools\sfc_result.txt"

Write-Host "=== [1/3] SFC 시스템 파일 검사 중... (3~10분 소요) ===" -ForegroundColor Yellow
$sfcResult = & sfc /scannow 2>&1
$sfcResult | Out-File $logPath -Encoding UTF8
$sfcResult | Write-Host

Write-Host "`n=== [2/3] DISM Windows 이미지 상태 점검 ===" -ForegroundColor Yellow
$dismScan = & dism /Online /Cleanup-Image /ScanHealth 2>&1
$dismScan | Write-Host

# ScanHealth에서 손상 발견 시 자동 복구
if ($dismScan -match "손상|component store corruption|repairable") {
    Write-Host "`n손상 발견 — RestoreHealth 복구 시작..." -ForegroundColor Red
    $dismRestore = & dism /Online /Cleanup-Image /RestoreHealth 2>&1
    $dismRestore | Write-Host
} else {
    Write-Host "DISM: 이상 없음" -ForegroundColor Green
}

Write-Host "`n=== [3/3] 주요 드라이브 파일시스템 빠른 점검 ===" -ForegroundColor Yellow
foreach ($drive in @("C:", "D:", "Q:")) {
    Write-Host "`n--- $drive 점검 ---"
    & chkdsk $drive /scan 2>&1 | Write-Host
}

Write-Host "`n=== 완료 ===" -ForegroundColor Green
