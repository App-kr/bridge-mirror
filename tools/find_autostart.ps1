# backup_daemon.py 자동실행 등록 위치 검색

Write-Host "=== Windows 작업 스케줄러 ==="
schtasks /query /fo LIST 2>$null | Select-String -Pattern "backup_daemon|Claudework|bridge" -Context 3

Write-Host ""
Write-Host "=== 시작프로그램 레지스트리 ==="
$regPaths = @(
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run",
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce"
)
foreach ($reg in $regPaths) {
    if (Test-Path $reg) {
        $items = Get-ItemProperty $reg -ErrorAction SilentlyContinue
        $items.PSObject.Properties | Where-Object { $_.Value -like "*backup*" -or $_.Value -like "*Claudework*" } |
            ForEach-Object { Write-Host "$($_.Name) = $($_.Value)" }
    }
}

Write-Host ""
Write-Host "=== 시작 폴더 ==="
$startupFolders = @(
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup",
    "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup"
)
foreach ($sf in $startupFolders) {
    if (Test-Path $sf) {
        Get-ChildItem $sf | Where-Object { $_.Name -like "*backup*" -or $_.Name -like "*bridge*" } |
            Select-Object Name, FullName | Format-Table -AutoSize
    }
}
