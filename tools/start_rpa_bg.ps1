param([int]$Limit = 10)

$rpaPy   = "Q:\Claudework\bridge base\craigslist_auto_rpa.py"
$logPath = "Q:\Claudework\bridge base\logs\craigslist_rpa.log"
$errPath = "Q:\Claudework\bridge base\logs\craigslist_rpa.err.log"
$pidFile = "Q:\Claudework\bridge base\craigslist_rpa.pid"

New-Item -ItemType Directory -Path "Q:\Claudework\bridge base\logs" -Force | Out-Null

if (Test-Path $pidFile) {
    $oldPid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($oldPid) {
        Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
        Write-Host "Previous process stopped (PID $oldPid)" -ForegroundColor Yellow
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

$process = Start-Process `
    -FilePath "python.exe" `
    -ArgumentList "`"$rpaPy`" --worker --limit=$Limit --no-relaunch" `
    -WorkingDirectory "Q:\Claudework\bridge base" `
    -RedirectStandardOutput $logPath `
    -RedirectStandardError $errPath `
    -NoNewWindow `
    -PassThru

$process.Id | Out-File -FilePath $pidFile -Encoding ASCII -Force

Write-Host ""
Write-Host "BRIDGE Craigslist RPA started in background" -ForegroundColor Green
Write-Host "PID  : $($process.Id)" -ForegroundColor Cyan
Write-Host "Log  : $logPath" -ForegroundColor Cyan
Write-Host "Stop : powershell -File tools\stop_rpa.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "Close this window anytime - RPA keeps running" -ForegroundColor Green
