Write-Host "=== Chrome Install Verify ==="
$paths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        $ver = (Get-Item $p).VersionInfo.FileVersion
        Write-Host "FOUND ($ver): $p" -ForegroundColor Green
    } else {
        Write-Host "NOT FOUND: $p" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Current Startup (HKLM Run) ==="
$run = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue
$run.PSObject.Properties | Where-Object { $_.Name -notmatch "^PS" } | ForEach-Object {
    Write-Host "  $($_.Name)"
}

Write-Host ""
Write-Host "=== Disabled Backup (HKLM Run_Disabled) ==="
$dis = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run_Disabled" -ErrorAction SilentlyContinue
if ($dis) {
    $dis.PSObject.Properties | Where-Object { $_.Name -notmatch "^PS" } | ForEach-Object {
        Write-Host "  [DISABLED] $($_.Name)" -ForegroundColor Gray
    }
} else {
    Write-Host "  (empty)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Windows Defender Chrome Exclusion ==="
$pref = Get-MpPreference -ErrorAction SilentlyContinue
$pref.ExclusionPath | ForEach-Object { if ($_ -imatch "chrome") { Write-Host "  Excluded: $_" -ForegroundColor Green } }
