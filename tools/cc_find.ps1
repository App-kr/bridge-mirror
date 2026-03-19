$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== 설치된 Adobe 프로그램 (레지스트리) ==="
$uninstallPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
)
foreach ($up in $uninstallPaths) {
    Get-ChildItem -Path $up -ErrorAction SilentlyContinue | ForEach-Object {
        $prop = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
        if ($prop.DisplayName -like "*Adobe*") {
            Write-Host "  $($prop.DisplayName)  [$($prop.DisplayVersion)]"
        }
    }
}

Write-Host "`n=== C:\Program Files\Adobe 폴더 ==="
if (Test-Path "C:\Program Files\Adobe") {
    Get-ChildItem "C:\Program Files\Adobe" | Select-Object Name | Format-Table -AutoSize
}

Write-Host "=== C:\Program Files (x86)\Adobe 폴더 ==="
if (Test-Path "C:\Program Files (x86)\Adobe") {
    Get-ChildItem "C:\Program Files (x86)\Adobe" | Select-Object Name | Format-Table -AutoSize
}

Write-Host "=== AcroTray 자동실행 ==="
Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue |
    Select-Object * -ExcludeProperty PS* | Format-List
