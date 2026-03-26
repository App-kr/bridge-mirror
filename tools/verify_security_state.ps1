# Final verification of all security states
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  BRIDGE Security State Verification" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# 1. RDP check
Write-Host "`n[1] RDP Access Control" -ForegroundColor Yellow
$rdpRules = Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object {
    ($_.DisplayName -match "Remote Desktop|RDP") -and $_.Direction -eq "Inbound" -and $_.Enabled -eq $true
}
foreach ($r in $rdpRules) {
    $filter = Get-NetFirewallAddressFilter -AssociatedNetFirewallRule $r -ErrorAction SilentlyContinue
    Write-Host "  Rule: $($r.DisplayName) | Action: $($r.Action) | Remote: $($filter.RemoteAddress)"
}

# 2. Tailscale
Write-Host "`n[2] Tailscale" -ForegroundColor Yellow
$tsIP = (Get-NetIPAddress | Where-Object { $_.IPAddress -match "^100\." }).IPAddress
if ($tsIP) {
    Write-Host "  Active: $tsIP" -ForegroundColor Green
    Write-Host "  RDP endpoint: ${tsIP}:3389"
} else {
    Write-Host "  WARNING: Tailscale not active!" -ForegroundColor Red
}

# 3. Chrome Remote Desktop
Write-Host "`n[3] Chrome Remote Desktop" -ForegroundColor Yellow
$crd = Get-NetFirewallRule -DisplayName "Chrome Remote Desktop Host" -ErrorAction SilentlyContinue
if ($crd -and $crd.Enabled -eq $true) {
    Write-Host "  Active (Google auth protected)" -ForegroundColor Green
} else {
    Write-Host "  Not found / Disabled" -ForegroundColor Red
}

# 4. Attack IP blocks
Write-Host "`n[4] Attack Country Blocks" -ForegroundColor Yellow
$blockRule = Get-NetFirewallRule -DisplayName "Block India-Turkey Attack Ranges" -ErrorAction SilentlyContinue
if ($blockRule -and $blockRule.Enabled) {
    $filter = Get-NetFirewallAddressFilter -AssociatedNetFirewallRule $blockRule -ErrorAction SilentlyContinue
    $count = @($filter.RemoteAddress).Count
    Write-Host "  Blocking $count IP ranges (IN+OUT)" -ForegroundColor Green
} else {
    Write-Host "  NOT ACTIVE - run block_attackers.ps1" -ForegroundColor Red
}

# 5. SMB check
Write-Host "`n[5] SMB (445) External Exposure" -ForegroundColor Yellow
$smbPublic = Get-NetFirewallRule -DisplayName "File and Printer Sharing (SMB-In)" -ErrorAction SilentlyContinue |
    Where-Object { $_.Profile -match "Public" -and $_.Enabled -and $_.Action -eq "Allow" }
if ($smbPublic) {
    Write-Host "  WARNING: SMB open on Public profile!" -ForegroundColor Red
} else {
    Write-Host "  OK - SMB restricted" -ForegroundColor Green
}

# 6. Open ports summary
Write-Host "`n[6] All Listening Ports (0.0.0.0)" -ForegroundColor Yellow
netstat -ano | Select-String "0.0.0.0" | Select-String "LISTENING"

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  Remote Access: Tailscale RDP + ChromeRD" -ForegroundColor Green
Write-Host "  RDP addr: ${tsIP}:3389  (Tailscale only)" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
