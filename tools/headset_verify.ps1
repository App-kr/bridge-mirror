# 수정 결과 검증
Write-Host "=== Task Scheduler 등록 확인 ===" -ForegroundColor Cyan
Get-ScheduledTask -TaskName "ABKO_N460_AutoConnect" -ErrorAction SilentlyContinue |
    Select-Object TaskName, State, Description | Format-List

Write-Host "=== USB Selective Suspend 적용 확인 ===" -ForegroundColor Cyan
$result = powercfg /query 381b4222-f694-41f0-9685-ff5bb260df2e 2a737441-1930-4402-8d77-b2bebba308a3 d4e98f31-5ffe-4ce1-be31-1b38b384c009 2>&1
Write-Host $result

Write-Host "`n=== AudioDeviceCmdlets 모듈 상태 ===" -ForegroundColor Cyan
$mod = Get-Module -ListAvailable -Name "AudioDeviceCmdlets" -ErrorAction SilentlyContinue
if ($mod) {
    Write-Host "AudioDeviceCmdlets 설치됨: OK" -ForegroundColor Green
} else {
    Write-Host "AudioDeviceCmdlets 없음 -> NirCmd 방식으로 대체" -ForegroundColor Yellow
}
