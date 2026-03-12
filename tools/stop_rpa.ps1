# BRIDGE Craigslist RPA 중단
$pidFile = "Q:\Claudework\bridge base\craigslist_rpa.pid"

if (Test-Path $pidFile) {
    $pid = Get-Content $pidFile
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    Remove-Item $pidFile -Force
    Write-Host "RPA 중단됨 (PID $pid)" -ForegroundColor Yellow
} else {
    Write-Host "실행 중인 RPA 없음" -ForegroundColor Gray
}
