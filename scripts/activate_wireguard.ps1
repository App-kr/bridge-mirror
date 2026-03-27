# WireGuard VPN 자동 활성화
# Activate WireGuard PC tunnel

Write-Host "WireGuard VPN 연결 중..." -ForegroundColor Cyan
Write-Host "=" * 70

$WGPath = "C:\Program Files\WireGuard"
$WGExe = "$WGPath\wireguard.exe"
$ConfigPath = "$WGPath\Data\Configurations\Scarlett_Main_PC.conf"

if (-not (Test-Path $WGExe)) {
    Write-Host "[ERR] WireGuard not found: $WGExe" -ForegroundColor Red
    exit 1
}

# Start WireGuard if not running
Write-Host "[IN] Starting WireGuard..." -ForegroundColor Yellow
$Process = Get-Process wireguard -ErrorAction SilentlyContinue
if (-not $Process) {
    & $WGExe
    Start-Sleep -Seconds 3
}

Write-Host "[OK] WireGuard started" -ForegroundColor Green

# Try wg-quick to activate tunnel
$WGQuick = "$WGPath\wg-quick.exe"
if (Test-Path $WGQuick) {
    Write-Host "[IN] Activating tunnel with wg-quick..." -ForegroundColor Yellow
    try {
        & $WGQuick up Scarlett_Main_PC
        Write-Host "[OK] Tunnel activated" -ForegroundColor Green
    } catch {
        Write-Host "[WARN] wg-quick failed, trying alternative method..." -ForegroundColor Yellow
    }
}

# Alternative: Use registry to enable interface
Write-Host "[IN] Checking tunnel status..." -ForegroundColor Yellow
$TunnelReg = "HKLM:\SYSTEM\CurrentControlSet\Services\WireGuardTunnel$Scarlett_Main_PC"
if (Test-Path $TunnelReg) {
    Write-Host "[OK] Tunnel registry found" -ForegroundColor Green
    try {
        Set-Service -Name "WireGuardTunnel$Scarlett_Main_PC" -StartupType Automatic
        Start-Service -Name "WireGuardTunnel$Scarlett_Main_PC" -ErrorAction SilentlyContinue
        Write-Host "[OK] Service started" -ForegroundColor Green
    } catch {
        Write-Host "[WARN] Service start failed" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=" * 70
Write-Host "[OK] VPN activation started" -ForegroundColor Green
Write-Host "=" * 70
Write-Host ""
Write-Host "Test:"
Write-Host "  ping 10.0.0.1"
Write-Host ""
