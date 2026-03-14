# BRIDGE Multi-Account Scheduler Launch
chcp 65001 > $null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$Host.UI.RawUI.WindowTitle = "BRIDGE Craig Scheduler"
$Host.UI.RawUI.BackgroundColor = "Black"
Clear-Host

Write-Host "" -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "  BRIDGE Multi-Account Scheduler" -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  account1: Coreabridge     01,07,13,19" -ForegroundColor Gray
Write-Host "  account2: airelair00      03,09,15,21" -ForegroundColor Gray
Write-Host "  account3: ferrari812fast  05,11,17,23" -ForegroundColor Gray
Write-Host ""
Write-Host "  Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host "  Close this window to stop scheduler." -ForegroundColor DarkYellow
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

Set-Location "K:\BridgeCraig"

$logFile = "K:\BridgeCraig\logs\scheduler.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $logFile -Value "[$timestamp] SCHEDULER START (multi-account)" -Encoding UTF8

try {
    & python scheduler.py --limit 10 2>&1
} catch {
    Write-Host "  [ERROR] $_" -ForegroundColor Red
    $errTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logFile -Value "[$errTime] SCHEDULER ERROR: $_" -Encoding UTF8
}

Write-Host ""
Write-Host "  Scheduler stopped." -ForegroundColor DarkGray
Start-Sleep -Seconds 5
