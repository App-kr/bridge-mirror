# WireGuard 복구 및 네트워크 정상화 스크립트
# Administrator 권한 필수

Write-Host "================================" -ForegroundColor Cyan
Write-Host "WireGuard 복구 + 네트워크 정상화" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 1. 관리자 권한 확인
$admin = [Security.Principal.WindowsIdentity]::GetCurrent().Groups -contains 'S-1-5-32-544'
if (-not $admin) {
    Write-Host "[ERR] 관리자 권한 필요. 관리자 권한으로 다시 실행하세요." -ForegroundColor Red
    exit 1
}

# 2. WireGuard 프로세스 종료
Write-Host "[1/5] WireGuard 프로세스 종료..." -ForegroundColor Yellow
Get-Process wireguard -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

# 3. WireGuard 서비스 비활성화
Write-Host "[2/5] WireGuard 서비스 비활성화..." -ForegroundColor Yellow
$services = Get-Service -Name 'WireGuardTunnel*' -ErrorAction SilentlyContinue
foreach ($svc in $services) {
    Write-Host "  - $($svc.Name) 중지 중..."
    Stop-Service -Name $svc.Name -Force -ErrorAction SilentlyContinue
    Set-Service -Name $svc.Name -StartupType Disabled -ErrorAction SilentlyContinue
    Write-Host "  - $($svc.Name) 비활성화 완료" -ForegroundColor Green
}

# 4. 네트워크 어댑터 복구
Write-Host "[3/5] 네트워크 어댑터 갱신..." -ForegroundColor Yellow
Get-NetAdapter | Where-Object { $_.Status -eq 'Down' } | Enable-NetAdapter -Confirm:$false -ErrorAction SilentlyContinue

# 5. DHCP 갱신
Write-Host "[4/5] DHCP 갱신 중..." -ForegroundColor Yellow
ipconfig /release 2>&1 | Out-Null
Start-Sleep -Seconds 2
ipconfig /renew 2>&1 | Out-Null
ipconfig /flushdns 2>&1 | Out-Null

# 6. 라우팅 테이블 초기화
Write-Host "[5/5] 라우팅 테이블 정리..." -ForegroundColor Yellow
route /c 2>&1 | Out-Null

Start-Sleep -Seconds 3

# 최종 상태 확인
Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "복구 완료. 현재 네트워크 상태:" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""

# 네트워크 어댑터 상태
Write-Host "📡 활성 어댑터:" -ForegroundColor Cyan
Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object Name, Status, MediaConnectionState | Format-Table

# 기본 게이트웨이
Write-Host "🔗 기본 게이트웨이:" -ForegroundColor Cyan
Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue | Select-Object DestinationPrefix, NextHop, RouteMetric | Format-Table

# DNS 서버
Write-Host "🔍 DNS 서버:" -ForegroundColor Cyan
Get-DnsClientServerAddress -AddressFamily IPv4 | Where-Object { $_.ServerAddresses -ne $null } | Select-Object InterfaceAlias, ServerAddresses | Format-Table

Write-Host ""
Write-Host "✅ 네트워크 복구 완료" -ForegroundColor Green
Write-Host "  Test: ping 8.8.8.8" -ForegroundColor Yellow
Write-Host ""
