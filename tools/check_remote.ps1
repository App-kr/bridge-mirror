Write-Host "=== Tailscale ===" -ForegroundColor Cyan
$ts = "C:\Program Files\Tailscale\tailscale.exe"
if (Test-Path $ts) {
    & $ts status
} else {
    Write-Host "Tailscale EXE not found at default path"
    Get-Process | Where-Object { $_.Name -match "tailscale" } | Select-Object Name, Id, Path
}

Write-Host "`n=== RDP Status ===" -ForegroundColor Cyan
$rdpVal = (Get-ItemProperty "HKLM:\System\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" -ErrorAction SilentlyContinue).fDenyTSConnections
if ($rdpVal -eq 0) { Write-Host "RDP: ENABLED" -ForegroundColor Green } else { Write-Host "RDP: DISABLED" -ForegroundColor Red }

Write-Host "`n=== Listening Ports (0.0.0.0) ===" -ForegroundColor Cyan
netstat -ano | Select-String "0.0.0.0" | Select-String "LISTENING"

Write-Host "`n=== Windows Firewall RDP Rules ===" -ForegroundColor Cyan
Get-NetFirewallRule -DisplayName "*Remote Desktop*" -ErrorAction SilentlyContinue |
    Select-Object DisplayName, Enabled, Direction, Action, Profile |
    Format-Table -AutoSize

Write-Host "`n=== Tailscale IP (100.x) ===" -ForegroundColor Cyan
Get-NetIPAddress | Where-Object { $_.IPAddress -match "^100\." } | Select-Object IPAddress, InterfaceAlias
