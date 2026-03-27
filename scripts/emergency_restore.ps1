# 긴급 네트워크 복구 스크립트
# WireGuard 구성 파일 제거 + 레지스트리 정리

Write-Host "================================" -ForegroundColor Red
Write-Host "긴급 네트워크 복구 (관리자 권한 필수)" -ForegroundColor Red
Write-Host "================================" -ForegroundColor Red
Write-Host ""

# 관리자 권한 확인
$admin = [Security.Principal.WindowsIdentity]::GetCurrent().Groups -contains 'S-1-5-32-544'
if (-not $admin) {
    Write-Host "[ERR] 관리자 권한 필요" -ForegroundColor Red
    exit 1
}

Write-Host "[1/8] WireGuard 프로세스 강제 종료..." -ForegroundColor Yellow
Get-Process wireguard -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process wg-quick -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

Write-Host "[2/8] WireGuard 구성 파일 제거..." -ForegroundColor Yellow
$configPath = "C:\Program Files\WireGuard\Data\Configurations\Scarlett_Main_PC.conf"
if (Test-Path $configPath) {
    Remove-Item $configPath -Force -ErrorAction SilentlyContinue
    Write-Host "  ✓ 제거됨: $configPath" -ForegroundColor Green
}

Write-Host "[3/8] WireGuard 서비스 강제 중지..." -ForegroundColor Yellow
$services = @(
    'WireGuardTunnel$Scarlett_Main_PC',
    'WireGuardTunnel',
    'WireGuard'
)
foreach ($svc in $services) {
    try {
        $service = Get-Service -Name $svc -ErrorAction SilentlyContinue
        if ($service) {
            Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
            Set-Service -Name $svc -StartupType Disabled -ErrorAction SilentlyContinue
            Write-Host "  ✓ 중지됨: $svc" -ForegroundColor Green
        }
    } catch {}
}
Start-Sleep -Seconds 2

Write-Host "[4/8] 네트워크 어댑터 상태 확인..." -ForegroundColor Yellow
Get-NetAdapter | ForEach-Object {
    if ($_.Status -eq 'Disabled') {
        Write-Host "  - $($_.Name) 활성화 중..."
        Enable-NetAdapter -Name $_.Name -Confirm:$false -ErrorAction SilentlyContinue
    }
}

Write-Host "[5/8] DHCP 강제 갱신..." -ForegroundColor Yellow
ipconfig /release *>$null
Start-Sleep -Seconds 1
ipconfig /renew *>$null
ipconfig /flushdns *>$null

Write-Host "[6/8] 라우팅 테이블 재설정..." -ForegroundColor Yellow
route /c *>$null

Write-Host "[7/8] Winsock 리셋..." -ForegroundColor Yellow
netsh winsock reset catalog *>$null
netsh int ipv4 reset *>$null

Write-Host "[8/8] 네트워크 서비스 재시작..." -ForegroundColor Yellow
Restart-Service -Name "Dhcp" -Force -ErrorAction SilentlyContinue
Restart-Service -Name "Dnscache" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "긴급 복구 완료" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "현재 상태:" -ForegroundColor Cyan
Write-Host ""
Write-Host "네트워크 어댑터:" -ForegroundColor White
Get-NetAdapter | Format-Table Name, Status, MediaConnectionState -AutoSize
Write-Host ""
Write-Host "기본 라우팅:" -ForegroundColor White
Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue | Format-Table DestinationPrefix, NextHop
Write-Host ""
Write-Host "⚡ 이후 단계:" -ForegroundColor Yellow
Write-Host "  1. 컴퓨터 재부팅 권장 (전체 초기화)"
Write-Host "  2. PowerShell에서: ping 8.8.8.8"
Write-Host "  3. 여전히 연결 안 되면: ipconfig /all (어댑터 IP 확인)"
Write-Host ""
