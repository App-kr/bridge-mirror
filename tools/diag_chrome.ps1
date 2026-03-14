# Chrome 삭제 원인 진단 스크립트
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== [1] 현재 사용자 ===" -ForegroundColor Cyan
Write-Host "User: $env:USERNAME"
Write-Host "Profile: $env:USERPROFILE"

Write-Host "`n=== [2] C:\Users 폴더 (임시프로필 확인) ===" -ForegroundColor Cyan
Get-ChildItem C:\Users -Force | Select-Object Name, LastWriteTime | Format-Table -AutoSize

Write-Host "=== [3] 복원/동결 소프트웨어 서비스 ===" -ForegroundColor Cyan
$restoreSvcs = Get-Service | Where-Object { $_.DisplayName -imatch "freeze|faronics|shadow|toolbox|reboot|restore|deep|rollback|returnil" }
if ($restoreSvcs) {
    $restoreSvcs | Select-Object Name, Status, DisplayName | Format-Table -AutoSize
} else {
    Write-Host "없음 (Deep Freeze 류 미감지)" -ForegroundColor Green
}

Write-Host "`n=== [4] Chrome 설치 경로 확인 ===" -ForegroundColor Cyan
$paths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Host "있음: $p" -ForegroundColor Green
    } else {
        Write-Host "없음: $p" -ForegroundColor Red
    }
}

Write-Host "`n=== [5] 예약 작업 (Chrome/Clean/Reset 관련) ===" -ForegroundColor Cyan
$tasks = Get-ScheduledTask | Where-Object { $_.TaskName -imatch "chrome|clean|delete|reset|restore" }
if ($tasks) {
    $tasks | Select-Object TaskName, State, TaskPath | Format-Table -AutoSize
} else {
    Write-Host "관련 예약 작업 없음" -ForegroundColor Green
}

Write-Host "`n=== [6] 레지스트리 — 임시 프로필 징후 확인 ===" -ForegroundColor Cyan
$profileList = Get-ChildItem "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
foreach ($key in $profileList) {
    $name = $key.PSChildName
    if ($name -match "\.bak$") {
        Write-Host "⚠️  .bak 키 발견 (임시 프로필 증거): $name" -ForegroundColor Red
    }
}
$bakCount = ($profileList | Where-Object { $_.PSChildName -match "\.bak$" }).Count
if ($bakCount -eq 0) { Write-Host ".bak 키 없음 (정상)" -ForegroundColor Green }

Write-Host "`n=== [7] Windows 재설정/업데이트 정책 확인 ===" -ForegroundColor Cyan
$resetPolicy = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore" -ErrorAction SilentlyContinue
Write-Host "시스템 복원 설정: $($resetPolicy | Out-String)"

Write-Host "`n=== [8] 프로그램 목록에서 복원 툴 검색 ===" -ForegroundColor Cyan
Get-ItemProperty "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
                 "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*" -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -imatch "freeze|faronics|shadow|toolbox|returnil|rollback|clean|reboot" } |
    Select-Object DisplayName, Publisher | Format-Table -AutoSize

Write-Host "`n진단 완료." -ForegroundColor Yellow
