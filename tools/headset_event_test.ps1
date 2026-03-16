# EventID 20001 발화 확인 + 이벤트 트리거 실제 테스트

Write-Host "=== 최근 EventID 20001 (USB 장치 연결) 이벤트 확인 ===" -ForegroundColor Cyan

# 1. 최근 20001 이벤트 조회 (USB 연결 시 발생 여부 확인)
try {
    $events = Get-WinEvent -ProviderName "Microsoft-Windows-UserPnp" -MaxEvents 50 -ErrorAction Stop |
              Where-Object { $_.Id -eq 20001 }

    if ($events) {
        Write-Host "최근 20001 이벤트 (${$events.Count}건):" -ForegroundColor Green
        $events | Select-Object -First 5 | ForEach-Object {
            Write-Host "  시각: $($_.TimeCreated) | 장치: $($_.Message -replace '.*장치 (.+?) 가.*','$1')"
        }
    } else {
        Write-Host "최근 20001 이벤트 없음" -ForegroundColor Yellow
    }
} catch {
    Write-Host "이벤트 조회 오류: $_" -ForegroundColor Red
}

# 2. 이벤트 채널 확인
Write-Host ""
Write-Host "=== 이벤트 채널 활성화 여부 ===" -ForegroundColor Cyan
try {
    $log = Get-WinEvent -ListLog "System" | Select-Object LogName, IsEnabled, RecordCount
    Write-Host "System 로그: IsEnabled=$($log.IsEnabled), 레코드=$($log.RecordCount)"
} catch { Write-Host "오류: $_" }

# 3. 이벤트 트리거 방식 검증 - 더 신뢰성 높은 방식으로 교체 테스트
Write-Host ""
Write-Host "=== 현재 Task 트리거 방식 검토 ===" -ForegroundColor Cyan
Write-Host "현재: EventID=20001 (Microsoft-Windows-UserPnp, System 로그)"
Write-Host ""

# System 로그에서 20001 이벤트 마지막 5건
try {
    $sysEvents = Get-WinEvent -LogName "System" -MaxEvents 1000 -ErrorAction Stop |
                 Where-Object { $_.Id -eq 20001 }
    if ($sysEvents) {
        Write-Host "System 로그 20001 이벤트 최근 5건:" -ForegroundColor Green
        $sysEvents | Select-Object -First 5 TimeCreated, Id, Message | Format-List
    } else {
        Write-Host "System 로그에 20001 없음 - 트리거 채널 확인 필요" -ForegroundColor Yellow
    }
} catch {
    Write-Host "System 로그 조회: $_"
}

# 4. 대안 트리거: Microsoft-Windows-Kernel-PnP/Configuration (더 신뢰성 높음)
Write-Host ""
Write-Host "=== 대안 채널 확인 (Kernel-PnP) ===" -ForegroundColor Cyan
try {
    $pnpEvents = Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -MaxEvents 50 -ErrorAction Stop
    Write-Host "Kernel-PnP 채널 활성: $($pnpEvents.Count)건 존재" -ForegroundColor Green
    $pnpEvents | Select-Object -First 3 TimeCreated, Id, Message | Format-List
} catch {
    Write-Host "Kernel-PnP 채널 접근 불가: $_" -ForegroundColor Yellow
}
