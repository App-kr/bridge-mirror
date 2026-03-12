$pidFile = "Q:\Claudework\bridge base\craigslist_rpa.pid"

if (Test-Path $pidFile) {
    $rpaPid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($rpaPid) {
        Stop-Process -Id $rpaPid -Force -ErrorAction SilentlyContinue
        Write-Host "RPA stopped (PID $rpaPid)" -ForegroundColor Yellow
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "No running RPA found" -ForegroundColor Gray
}
