$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== Adobe 예약 작업 ==="
Get-ScheduledTask | Where-Object { $_.TaskName -like "*Adobe*" -or $_.TaskPath -like "*Adobe*" } | Select-Object TaskName, TaskPath, State | Format-Table -AutoSize

Write-Host "=== Acrobat 업데이트 레지스트리 ==="
$regPaths = @(
    "HKLM:\SOFTWARE\Adobe\Acrobat Reader\DC\Installer",
    "HKLM:\SOFTWARE\Adobe\Adobe Acrobat\DC\Installer",
    "HKLM:\SOFTWARE\Policies\Adobe\Acrobat Reader\DC\FeatureLockDown",
    "HKLM:\SOFTWARE\WOW6432Node\Adobe\Acrobat Reader\DC\Installer",
    "HKLM:\SOFTWARE\WOW6432Node\Adobe\Adobe Acrobat\DC\Installer"
)
foreach ($p in $regPaths) {
    if (Test-Path $p) {
        Write-Host $p
        Get-ItemProperty $p | Select-Object * -ExcludeProperty PSPath, PSParentPath, PSChildName, PSDrive, PSProvider | Format-List
    }
}

Write-Host "=== 실행 중인 Adobe 프로세스 ==="
Get-Process | Where-Object { $_.Name -like "*Adobe*" -or $_.Name -like "*Acrobat*" } | Select-Object Name, Id | Format-Table -AutoSize
