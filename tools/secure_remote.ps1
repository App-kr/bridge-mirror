# STEP 1: RDP -> Tailscale only (100.64.0.0/10)
Write-Host "[STEP 1] Locking RDP to Tailscale subnet only..." -ForegroundColor Yellow

# Disable all existing RDP inbound rules
$rdpRules = Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object {
    $_.DisplayName -match "Remote Desktop" -and $_.Direction -eq "Inbound" -and $_.Action -eq "Allow"
}
foreach ($rule in $rdpRules) {
    if ($rule.DisplayName -notmatch "Chrome") {
        Disable-NetFirewallRule -Name $rule.Name -ErrorAction SilentlyContinue
        Write-Host "  Disabled: $($rule.DisplayName)"
    }
}

# Remove old Tailscale RDP rule if exists
Remove-NetFirewallRule -DisplayName "RDP via Tailscale Only" -ErrorAction SilentlyContinue

# Allow RDP only from Tailscale CGNAT range (100.64.0.0/10)
New-NetFirewallRule `
    -DisplayName "RDP via Tailscale Only" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 3389 `
    -RemoteAddress "100.64.0.0/10" `
    -Action Allow `
    -Profile Any `
    -Enabled True | Out-Null

Write-Host "  [OK] RDP now restricted to Tailscale (100.64.0.0/10) only" -ForegroundColor Green

# STEP 2: Block SMB (445) from external - allow only LAN + Tailscale
Write-Host "`n[STEP 2] Locking SMB (445) to LAN + Tailscale only..." -ForegroundColor Yellow

Remove-NetFirewallRule -DisplayName "SMB Secure (LAN+Tailscale)" -ErrorAction SilentlyContinue

New-NetFirewallRule `
    -DisplayName "SMB Secure (LAN+Tailscale)" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 445 `
    -RemoteAddress "192.168.0.0/16","10.0.0.0/8","172.16.0.0/12","100.64.0.0/10" `
    -Action Allow `
    -Profile Any `
    -Enabled True | Out-Null

# Block SMB from everything else
Remove-NetFirewallRule -DisplayName "SMB Block External" -ErrorAction SilentlyContinue
New-NetFirewallRule `
    -DisplayName "SMB Block External" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 445 `
    -RemoteAddress "Any" `
    -Action Block `
    -Profile Public `
    -Enabled True | Out-Null

Write-Host "  [OK] SMB locked to LAN + Tailscale only" -ForegroundColor Green

# STEP 3: Block WinRM (5985/5986) if open
Write-Host "`n[STEP 3] Blocking WinRM from external..." -ForegroundColor Yellow
Remove-NetFirewallRule -DisplayName "WinRM Block External" -ErrorAction SilentlyContinue
New-NetFirewallRule `
    -DisplayName "WinRM Block External" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort @(5985, 5986) `
    -RemoteAddress "Any" `
    -Action Block `
    -Profile Public `
    -Enabled True | Out-Null
Write-Host "  [OK] WinRM blocked on Public profile" -ForegroundColor Green

# STEP 4: Verify
Write-Host "`n=== Verification ===" -ForegroundColor Cyan
Write-Host "RDP Rules:"
Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object {
    ($_.DisplayName -match "Remote Desktop|RDP") -and $_.Direction -eq "Inbound"
} | Select-Object DisplayName, Enabled, Action | Format-Table -AutoSize

Write-Host "Active Tailscale IP:"
Get-NetIPAddress | Where-Object { $_.IPAddress -match "^100\." } | Select-Object IPAddress, InterfaceAlias

Write-Host "`nDone. Remote access now requires Tailscale tunnel." -ForegroundColor Green
Write-Host "RDP: connect to 100.76.177.40:3389 via Tailscale" -ForegroundColor Cyan
Write-Host "Chrome Remote Desktop: still active (Google auth)" -ForegroundColor Cyan
