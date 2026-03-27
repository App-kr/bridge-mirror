# WireGuard PC Auto Install Script
# Requires Administrator

#Requires -RunAsAdministrator

Write-Host "Installing WireGuard PC Client..." -ForegroundColor Cyan
Write-Host "=" * 70

# 1. Check installation
$WGPath = "C:\Program Files\WireGuard"
$WGExe = "$WGPath\wireguard.exe"

if (Test-Path $WGExe) {
    Write-Host "[OK] WireGuard already installed" -ForegroundColor Green
} else {
    Write-Host "[IN] Installing WireGuard..." -ForegroundColor Yellow
    $Installer = "C:\Users\Scarlett\Desktop\wireguard-installer.exe"

    if (Test-Path $Installer) {
        & $Installer /install | Out-Null
        Start-Sleep -Seconds 5
        Write-Host "[OK] WireGuard installation complete" -ForegroundColor Green
    } else {
        Write-Host "[ERR] Installer not found: $Installer" -ForegroundColor Red
        exit 1
    }
}

# 2. Generate PC keys
Write-Host "[IN] Generating PC WireGuard keys..." -ForegroundColor Yellow

$ConfigDir = "$WGPath\Data\Configurations"
if (-not (Test-Path $ConfigDir)) {
    New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null
}

# Generate private key / public key
$WgCmd = "$WGPath\wg.exe"
$PrivateKey = & $WgCmd genkey
$PublicKey = $PrivateKey | & $WgCmd pubkey

Write-Host "[OK] PC WireGuard keys generated" -ForegroundColor Green
Write-Host "   Private Key: $($PrivateKey.Substring(0, 20))..." -ForegroundColor Gray
Write-Host "   Public Key:  $($PublicKey.Substring(0, 20))..." -ForegroundColor Gray

# 3. Create PC config file
$PCConfPath = "$ConfigDir\Scarlett_Main_PC.conf"
$PCConfContent = @"
[Interface]
PrivateKey = $PrivateKey
Address = 10.0.0.2/32
DNS = 8.8.8.8, 8.8.4.4
SaveMconfig = false

[Peer]
PublicKey = SERVER_PUBLIC_KEY_HERE
Endpoint = bridgejob.co.kr:51820
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
"@

Set-Content -Path $PCConfPath -Value $PCConfContent -Encoding UTF8
Write-Host "[OK] Config file created: $PCConfPath" -ForegroundColor Green

# 4. Save registration info
$RegistrationInfo = @{
    device_name = "Scarlett_Main_PC"
    public_key = $PublicKey
    vpn_ip = "10.0.0.2"
    created = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
}

$RegistrationPath = "Q:\Claudework\bridge base\security_config\wireguard\pc\registration.json"
$RegistrationInfo | ConvertTo-Json | Set-Content -Path $RegistrationPath -Encoding UTF8
Write-Host "[OK] Registration info saved: $RegistrationPath" -ForegroundColor Green

# 5. Router registration guide
Write-Host ""
Write-Host "NEXT STEP - Register PC public key in router:" -ForegroundColor Cyan
Write-Host "=" * 70
Write-Host "1. Access 192.168.0.1 (admin/admin)"
Write-Host "2. Advanced > Security > WireGuard > Add Peer"
Write-Host "3. Enter:"
Write-Host "   Name: Scarlett_Main_PC"
Write-Host "   Public Key:"
Write-Host "   $PublicKey" -ForegroundColor Yellow
Write-Host "   IP: 10.0.0.2"
Write-Host "4. Save and restart WireGuard server"
Write-Host ""

# 6. Enable WireGuard service
Write-Host "[IN] Configuring WireGuard service..." -ForegroundColor Yellow
$Service = Get-Service WireGuardTunnel -ErrorAction SilentlyContinue
if ($Service) {
    Set-Service -Name WireGuardTunnel -StartupType Automatic
    Write-Host "[OK] WireGuard service auto-start enabled" -ForegroundColor Green
} else {
    Write-Host "[WARN] WireGuard service not found (reboot may be needed)" -ForegroundColor Yellow
}

# 7. Launch WireGuard
Write-Host ""
Write-Host "[IN] Launching WireGuard app..." -ForegroundColor Yellow
Start-Process $WGExe

Write-Host ""
Write-Host "=" * 70
Write-Host "[OK] Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Register PC public key in router (see above)"
Write-Host "2. In WireGuard app, enable 'Scarlett_Main_PC' tunnel"
Write-Host "3. Test VPN: ping 10.0.0.1"
Write-Host ""
