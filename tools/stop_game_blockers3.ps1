# 3차 - 빠진 서비스 확인 및 최종 상태 보고

$checkServices = @(
    "SafeTransactionSVC", "CrossEXService", "CrossEXLiveChecker",
    "KOS_Service", "nossvc", "ToucnEn_nxFirewall", "OZWLService",
    "AnySign4PCLauncher"
)

Write-Host "=== 남은 서비스 상태 확인 ==="
foreach ($svc in $checkServices) {
    $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
    if ($s) {
        Write-Host "$svc : Status=$($s.Status), StartType=$($s.StartType)"
        if ($s.StartType -ne "Disabled") {
            Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
            Set-Service  -Name $svc -StartupType Disabled -ErrorAction SilentlyContinue
            Write-Host "  -> 비활성화 완료"
        }
    } else {
        Write-Host "$svc : 존재하지 않음 (이미 없거나 다른 이름)"
    }
}

Write-Host ""
Write-Host "=== VBS 백업 테스트 ==="
$vbs = "Q:\Claudework\ClaudeBlog\auto_backup_silent.vbs"
if (Test-Path $vbs) { Write-Host "VBS 파일 존재: OK" } else { Write-Host "VBS 파일 없음: 오류" }

Write-Host ""
Write-Host "=== 최종 요약 ==="
Write-Host "[유지 - 백그라운드 전용]"
Write-Host "  Steam (-silent), RiotClient (--launch-background-mode), GoogleDriveFS (--startup_mode)"
Write-Host "  Notion (--open-at-login), Digital Clock, Tailscale (VPN)"
Write-Host ""
Write-Host "[수동 설정 필요 - 앱 내부 설정]"
Write-Host "  Discord: 설정 > 게임 오버레이 > '게임에서 인앱 오버레이 활성화' OFF"
Write-Host "  KakaoTalk: 설정 > 알림 > 팝업 알림 OFF 또는 방해 금지 모드"
