$ErrorActionPreference = 'SilentlyContinue'

# 1. Check Chrome User Data for profile shortcuts (recreated by Chrome on update)
Write-Host "=== Chrome Profile Shortcuts in User Data ==="
$userDataDir = "$env:LOCALAPPDATA\Google\Chrome\User Data"
if (Test-Path $userDataDir) {
    $profileShortcuts = Get-ChildItem $userDataDir -Filter "*.lnk" -Recurse
    $shell = New-Object -ComObject WScript.Shell
    foreach ($lnk in $profileShortcuts) {
        $sc = $shell.CreateShortcut($lnk.FullName)
        $ok = if (Test-Path $sc.TargetPath) { "[OK]" } else { "[BROKEN]" }
        Write-Host "$ok $($lnk.Name) -> $($sc.TargetPath)"
    }
    if ($profileShortcuts.Count -eq 0) { Write-Host "None found" }
} else {
    Write-Host "User Data dir not found"
}

# 2. Check desktop hidden/all files
Write-Host ""
Write-Host "=== Desktop ALL files (including hidden) ==="
Get-ChildItem "$env:USERPROFILE\Desktop" -Force | Select-Object Name, Attributes | Format-Table -AutoSize

# 3. Check if there's a broken shortcut with empty target - delete it
Write-Host ""
Write-Host "=== Checking/Fixing broken -.lnk on Desktop ==="
$brokenLnk = "$env:USERPROFILE\Desktop\-.lnk"
if (Test-Path $brokenLnk) {
    $shell = New-Object -ComObject WScript.Shell
    $sc = $shell.CreateShortcut($brokenLnk)
    Write-Host "Found -.lnk with target: '$($sc.TargetPath)'"
    if ([string]::IsNullOrWhiteSpace($sc.TargetPath)) {
        Remove-Item $brokenLnk -Force
        Write-Host "[DELETED] Empty/broken -.lnk removed from Desktop"
    }
}

# 4. Check Chrome's Last known version and current default
Write-Host ""
Write-Host "=== Chrome Version Info ==="
$versions = Get-ChildItem "D:\Google\ProgramFiles\Chrome\Application" -Directory | Where-Object { $_.Name -match "^\d+" } | Sort-Object Name
foreach ($v in $versions) {
    Write-Host "Version dir: $($v.Name)"
}
$chromeVer = (Get-Item "D:\Google\ProgramFiles\Chrome\Application\chrome.exe").VersionInfo.FileVersion
Write-Host "Active chrome.exe version: $chromeVer"

# 5. Check registry for Chrome install path
Write-Host ""
Write-Host "=== Chrome Registry Install Path ==="
$regPaths = @(
    "HKCU:\Software\Google\Chrome\BLBeacon",
    "HKLM:\SOFTWARE\Google\Chrome",
    "HKLM:\SOFTWARE\WOW6432Node\Google\Chrome"
)
foreach ($rp in $regPaths) {
    if (Test-Path $rp) {
        Write-Host "Registry: $rp"
        Get-ItemProperty $rp | Select-Object * -ExcludeProperty PS* | Format-List
    }
}
