$ErrorActionPreference = 'SilentlyContinue'

$newProxy = "D:\Google\ProgramFiles\Chrome\Application\chrome_proxy.exe"
$newExe   = "D:\Google\ProgramFiles\Chrome\Application\chrome.exe"
$userDataDir = "$env:LOCALAPPDATA\Google\Chrome\User Data"

Write-Host "=== Fixing Chrome User Data broken shortcuts ==="
Write-Host "New target: $newProxy"
Write-Host ""

$shell = New-Object -ComObject WScript.Shell
$fixed = 0
$failed = 0

$lnkFiles = Get-ChildItem $userDataDir -Filter "*.lnk" -Recurse
foreach ($lnk in $lnkFiles) {
    $sc = $shell.CreateShortcut($lnk.FullName)
    $target = $sc.TargetPath

    # Only fix shortcuts pointing to C drive (old path)
    if ($target -like "C:\*chrome_proxy*" -or $target -like "C:\*chrome.exe*") {
        Write-Host "FIXING: $($lnk.FullName)"
        Write-Host "  OLD: $target"

        # Preserve arguments (profile info is in Arguments)
        $args = $sc.Arguments

        $sc.TargetPath = $newProxy
        $sc.IconLocation = "$newExe,0"
        $sc.Save()

        Write-Host "  NEW: $newProxy"
        Write-Host "  ARG: $args"
        $fixed++
    }
}

Write-Host ""
Write-Host "Fixed: $fixed shortcuts"
Write-Host ""

# Verify
Write-Host "=== Verification ==="
$lnkFiles2 = Get-ChildItem $userDataDir -Filter "*.lnk" -Recurse
foreach ($lnk in $lnkFiles2) {
    $sc = $shell.CreateShortcut($lnk.FullName)
    $ok = if (Test-Path $sc.TargetPath) { "[OK]" } else { "[BROKEN]" }
    Write-Host "$ok $($lnk.Name)"
}

# Also fix Start Menu Chrome Apps shortcuts if any still broken
Write-Host ""
Write-Host "=== Start Menu Chrome Apps shortcuts ==="
$startMenuApps = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Chrome Apps"
if (Test-Path $startMenuApps) {
    $lnks = Get-ChildItem $startMenuApps -Filter "*.lnk"
    foreach ($lnk in $lnks) {
        $sc = $shell.CreateShortcut($lnk.FullName)
        $ok = if (Test-Path $sc.TargetPath) { "[OK]" } else { "[BROKEN]" }
        Write-Host "$ok $($lnk.Name) -> $($sc.TargetPath)"
    }
}

Write-Host ""
Write-Host "Done. Please restart Chrome once to let it verify shortcuts."
