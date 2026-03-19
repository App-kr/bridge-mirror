$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== Creative Cloud 서비스 ==="
Get-Service | Where-Object { $_.DisplayName -like "*Adobe*" -or $_.Name -like "*Adobe*" -or $_.Name -like "*CC*" } |
    Select-Object Name, DisplayName, Status, StartType | Format-Table -AutoSize

Write-Host "=== Creative Cloud 실행 중 프로세스 ==="
Get-Process | Where-Object {
    $_.Name -like "*Creative*" -or $_.Name -like "*CCX*" -or $_.Name -like "*AdobeIPC*" -or
    $_.Name -like "*CoreSync*" -or $_.Name -like "*CCLib*" -or $_.Name -like "*AdobeDesktop*" -or
    $_.Name -like "*CCDaemon*" -or $_.Name -like "*Adobe*"
} | Select-Object Name, Id | Format-Table -AutoSize

Write-Host "=== Creative Cloud 자동실행 (레지스트리) ==="
$runPaths = @(
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"
)
foreach ($rp in $runPaths) {
    if (Test-Path $rp) {
        $props = Get-ItemProperty -Path $rp
        $props.PSObject.Properties | Where-Object { $_.Name -like "*Adobe*" -or $_.Name -like "*CC*" -or $_.Value -like "*Adobe*" } |
            ForEach-Object { Write-Host "  [$($_.Name)] = $($_.Value)" }
    }
}

Write-Host "=== CC 설치 경로 확인 ==="
$ccPaths = @(
    "C:\Program Files (x86)\Adobe\Adobe Creative Cloud",
    "C:\Program Files\Adobe\Adobe Creative Cloud",
    "C:\Program Files (x86)\Common Files\Adobe\Creative Cloud Libraries",
    "C:\Program Files (x86)\Common Files\Adobe\OOBE"
)
foreach ($p in $ccPaths) {
    if (Test-Path $p) { Write-Host "  EXISTS: $p" }
}

Write-Host "=== 예약 작업 (Adobe) ==="
Get-ScheduledTask | Where-Object { $_.TaskName -like "*Adobe*" -or $_.TaskPath -like "*Adobe*" } |
    Select-Object TaskName, State | Format-Table -AutoSize
