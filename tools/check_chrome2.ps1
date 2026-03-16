$ErrorActionPreference = 'SilentlyContinue'

# D Drive Chrome check
Write-Host "=== D Drive Chrome Check ==="
$proxy = "D:\Google\ProgramFiles\Chrome\Application\chrome_proxy.exe"
$exe   = "D:\Google\ProgramFiles\Chrome\Application\chrome.exe"
if (Test-Path $proxy) { Write-Host "[OK] chrome_proxy.exe EXISTS" } else { Write-Host "[MISSING] chrome_proxy.exe" }
if (Test-Path $exe)   { Write-Host "[OK] chrome.exe EXISTS" }       else { Write-Host "[MISSING] chrome.exe" }

$chromeDir = "D:\Google\ProgramFiles\Chrome\Application"
if (Test-Path $chromeDir) {
    Write-Host ""
    Write-Host "Files in $chromeDir :"
    Get-ChildItem $chromeDir | Select-Object Name | Format-Table -AutoSize
}

# Desktop shortcuts
Write-Host "=== Desktop Shortcuts ==="
$shell = New-Object -ComObject WScript.Shell
$desktops = @(
    "$env:USERPROFILE\Desktop",
    "C:\Users\Public\Desktop"
)
foreach ($d in $desktops) {
    if (-not (Test-Path $d)) { continue }
    $lnks = Get-ChildItem $d -Filter "*.lnk"
    foreach ($lnk in $lnks) {
        $sc = $shell.CreateShortcut($lnk.FullName)
        $ok = if (Test-Path $sc.TargetPath) { "[OK]" } else { "[BROKEN]" }
        Write-Host "$ok $($lnk.Name) -> $($sc.TargetPath)"
    }
}

# Chrome auto-update service check
Write-Host ""
Write-Host "=== Chrome Update Services ==="
Get-Service -Name "GoogleChromeElevationService","gupdate","gupdatem" | Select-Object Name, Status, StartType | Format-Table -AutoSize
