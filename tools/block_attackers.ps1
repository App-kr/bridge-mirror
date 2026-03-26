# Block major IP ranges from India and Turkey (top attack sources)
# These are the most active attack ranges seen in logs

Write-Host "Blocking India + Turkey attack IP ranges..." -ForegroundColor Yellow

# India major ISP ranges (Jio, BSNL, Airtel, Reliance - common attack sources)
$indiaRanges = @(
    "103.0.0.0/8",      # India APNIC
    "103.21.244.0/22",
    "27.116.0.0/14",
    "49.32.0.0/11",
    "49.248.0.0/14",
    "61.0.0.0/11",
    "103.100.0.0/14",
    "117.192.0.0/10",
    "122.160.0.0/11",
    "122.164.0.0/14",
    "223.176.0.0/12",
    "223.240.0.0/13",
    "182.68.0.0/14",
    "182.72.0.0/15",
    "106.51.0.0/16",
    "106.208.0.0/12",
    "59.88.0.0/13",
    "59.96.0.0/13"
)

# Turkey major ISP ranges (Turk Telekom, Vodafone TR, Turkcell)
$turkeyRanges = @(
    "78.160.0.0/11",    # Turk Telekom
    "88.228.0.0/14",    # Turk Telekom
    "88.232.0.0/13",
    "176.220.0.0/14",   # Turkcell
    "176.236.0.0/14",
    "5.24.0.0/13",      # Vodafone TR
    "31.145.0.0/16",
    "95.0.0.0/10",
    "213.14.0.0/16",
    "212.154.0.0/16"
)

$allRanges = $indiaRanges + $turkeyRanges

# Remove old rule
Remove-NetFirewallRule -DisplayName "Block India-Turkey Attack Ranges" -ErrorAction SilentlyContinue

# Create single block rule with all ranges
New-NetFirewallRule `
    -DisplayName "Block India-Turkey Attack Ranges" `
    -Direction Inbound `
    -RemoteAddress $allRanges `
    -Action Block `
    -Profile Any `
    -Enabled True `
    -Description "Blocks major Indian and Turkish ISP ranges (active attack sources)" | Out-Null

Write-Host "  [OK] Blocked $($allRanges.Count) IP ranges" -ForegroundColor Green

# Also block these ranges for outbound (prevents callback if malware exists)
Remove-NetFirewallRule -DisplayName "Block India-Turkey Outbound" -ErrorAction SilentlyContinue
New-NetFirewallRule `
    -DisplayName "Block India-Turkey Outbound" `
    -Direction Outbound `
    -RemoteAddress $allRanges `
    -Action Block `
    -Profile Any `
    -Enabled True `
    -Description "Blocks outbound to Indian and Turkish ranges" | Out-Null

Write-Host "  [OK] Outbound also blocked (malware callback prevention)" -ForegroundColor Green
Write-Host "`nDone. $($allRanges.Count) ranges blocked (inbound + outbound)." -ForegroundColor Cyan
