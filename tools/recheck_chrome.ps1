$ErrorActionPreference = 'SilentlyContinue'
$shell = New-Object -ComObject WScript.Shell

$broken = 0
$ok = 0

Write-Host "=== FULL Chrome Shortcut Recheck ==="
Write-Host ""

# All locations to scan
$searchDirs = @(
    "$env:USERPROFILE\Desktop",
    "C:\Users\Public\Desktop",
    "C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs",
    "$env:APPDATA\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar",
    "$env:LOCALAPPDATA\Google\Chrome\User Data"
)

foreach ($dir in $searchDirs) {
    if (-not (Test-Path $dir)) { continue }
    $lnks = Get-ChildItem $dir -Filter "*.lnk" -Recurse
    foreach ($lnk in $lnks) {
        $sc = $shell.CreateShortcut($lnk.FullName)
        $target = $sc.TargetPath
        if ($target -like "*chrome*") {
            if (Test-Path $target) {
                Write-Host "[OK]     $($lnk.Name)"
                Write-Host "         -> $target"
                $ok++
            } else {
                Write-Host "[BROKEN] $($lnk.Name)"
                Write-Host "         -> $target"
                $broken++
            }
        }
    }
}

Write-Host ""
Write-Host "=============================="
Write-Host "OK: $ok   BROKEN: $broken"
if ($broken -eq 0) {
    Write-Host "RESULT: PASS - No broken Chrome shortcuts"
} else {
    Write-Host "RESULT: FAIL - $broken broken shortcut(s) remain"
}
