$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== AGS Service Status ==="
Get-Service | Where-Object { $_.Name -like '*AGS*' -or $_.Name -like '*AdobeGenuine*' -or $_.Name -like '*AdobeARM*' } | Select-Object Name, Status, StartType | Format-Table -AutoSize

Write-Host "=== AGS Process Status ==="
Get-Process | Where-Object { $_.Name -like '*AGS*' -or $_.Name -like '*AdobeGC*' -or $_.Name -like '*AGCInvoker*' -or $_.Name -like '*AdobeARM*' } | Select-Object Name, Id | Format-Table -AutoSize

Write-Host "=== AGS Executable Locations ==="
$paths = @(
    "C:\Program Files (x86)\Common Files\Adobe\AdobeGCClient",
    "C:\Program Files\Common Files\Adobe\AdobeGCClient",
    "C:\Program Files (x86)\Common Files\Adobe\ARM\1.0",
    "C:\Program Files\Common Files\Adobe\ARM\1.0"
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Host "  PATH: $p"
        Get-ChildItem $p -Filter "*.exe" -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "    $($_.FullName)" }
    }
}

Write-Host ""
Write-Host "=== Adobe Scheduled Tasks ==="
Get-ScheduledTask | Where-Object { $_.TaskName -like "*Adobe*" } | Select-Object TaskName, State | Format-Table -AutoSize

Write-Host ""
Write-Host "=== Adobe Firewall Rules (existing) ==="
Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*Adobe*" } | Select-Object DisplayName, Direction, Action | Format-Table -AutoSize
