# Check HKCU startup entries too
Write-Host "=== HKCU Startup Entries ==="
$hkcu = Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue
if ($hkcu) {
    $hkcu.PSObject.Properties | Where-Object { $_.Name -notmatch "^PS" } | ForEach-Object {
        $flag = ""
        if ($_.Name -imatch "crossex|magic|veraport") { $flag = " <-- SUSPICIOUS" }
        Write-Host "  $($_.Name)$flag"
    }
}

# Disable CrossEX and MagicLine from HKCU if present
Write-Host ""
Write-Host "=== Disabling CrossEX / MagicLine from HKCU ==="
$disableHkcu = @("CrossEXService", "MagicLine4NPIZ", "wizvera-veraport-x64")
foreach ($name in $disableHkcu) {
    $existing = Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -Name $name -ErrorAction SilentlyContinue
    if ($existing) {
        Remove-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -Name $name -ErrorAction SilentlyContinue
        Write-Host "  Disabled (HKCU): $name" -ForegroundColor Green
    }
}

# Also check HKLM for CrossEX/MagicLine and disable
$disableHklm = @("CrossEXService", "MagicLine4NPIZ")
foreach ($name in $disableHklm) {
    $existing = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -Name $name -ErrorAction SilentlyContinue
    if ($existing) {
        Remove-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -Name $name -ErrorAction SilentlyContinue
        Write-Host "  Disabled (HKLM): $name" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "=== Final HKLM Run ==="
$run = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue
$run.PSObject.Properties | Where-Object { $_.Name -notmatch "^PS" } | ForEach-Object { Write-Host "  $($_.Name)" }

Write-Host ""
Write-Host "=== Final HKCU Run ==="
$hkcu2 = Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue
$hkcu2.PSObject.Properties | Where-Object { $_.Name -notmatch "^PS" } | ForEach-Object { Write-Host "  $($_.Name)" }
