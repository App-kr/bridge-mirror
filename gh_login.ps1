$Host.UI.RawUI.WindowTitle = "GitHub Login - koreadobby"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  GitHub Login (koreadobby)" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  When 8-digit code appears, press Enter to open browser." -ForegroundColor White
Write-Host "  Login as 'koreadobby' account, paste code, click Authorize." -ForegroundColor White
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

gh auth login --hostname github.com --git-protocol https --web

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
if ($LASTEXITCODE -eq 0) {
    Write-Host "  SUCCESS - Tell Claude: '됐어'" -ForegroundColor Green
} else {
    Write-Host "  FAILED - Tell Claude what happened" -ForegroundColor Red
}
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to close"
