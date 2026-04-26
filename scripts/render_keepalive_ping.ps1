# BRIDGE Render Free Keepalive Ping
# 20분마다 /api/health 호출 → cold start 방지
# 한 달 한도 750hr 안전: 20분 간격 = 일 72회 = 한 달 ~2200회
# 응답코드/지연 무시, 절대 실패 안 함 (catch all)
$ErrorActionPreference = "SilentlyContinue"
try {
    $null = Invoke-WebRequest -Uri 'https://bridge-n7hk.onrender.com/api/health' `
        -UseBasicParsing -TimeoutSec 30 -ErrorAction SilentlyContinue
} catch {
    # 일시적 네트워크 오류 무시 (cron 다음 슬롯에서 재시도)
}
exit 0
