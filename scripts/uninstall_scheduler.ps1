# BRIDGE 스케줄러 제거
$taskName = "BRIDGE_Craig_Scheduler"
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "  스케줄러 제거 완료" -ForegroundColor Green
} else {
    Write-Host "  등록된 스케줄러 없음" -ForegroundColor Yellow
}
