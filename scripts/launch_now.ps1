# BRIDGE Craigslist RPA — Manual Launch
chcp 65001 > $null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$Host.UI.RawUI.WindowTitle = "BRIDGE Craig RPA"
Clear-Host

$BASE = "Q:\Claudework\bridge base"
$PY   = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe"
Set-Location $BASE

# 계정 선택 팝업
Write-Host "  계정 선택 팝업을 확인하세요..." -ForegroundColor Cyan
$accountResult = & $PY -c "import sys; sys.path.insert(0,'$BASE'); from rpa_overlay import ask_account_selection; r = ask_account_selection(); print(r if r is not None else 'DEFAULT')" 2>&1
$accountResult = "$accountResult".Trim()

if ($accountResult -eq "CANCEL") {
    Write-Host "  취소되었습니다." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    exit
}

if ($accountResult -eq "DEFAULT" -or $accountResult -eq "None") {
    $accountArg = ""
    $accountLabel = "default"
} else {
    $accountArg = "--account $accountResult"
    $accountLabel = $accountResult
}

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "  BRIDGE Craigslist RPA Running..." -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host "  Account: $accountLabel" -ForegroundColor Gray
Write-Host "  Mode: headless (background Chrome)" -ForegroundColor Gray
Write-Host "  Limit: 10 posts per run" -ForegroundColor Gray
Write-Host ""
Write-Host "  Close this window anytime to stop." -ForegroundColor DarkYellow
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

$startTime = Get-Date
$logFile = "$BASE\logs\scheduler.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $logFile -Value "[$timestamp] RPA MANUAL START ($accountLabel)"

try {
    if ($accountArg) {
        & $PY "$BASE\craigslist_auto_rpa.py" --headless --limit 10 --account $accountResult 2>&1
    } else {
        & $PY "$BASE\craigslist_auto_rpa.py" --headless --limit 10 2>&1
    }
    $cmd = ""  # unused
    $exitCode = $LASTEXITCODE
    $elapsed = [math]::Round(((Get-Date) - $startTime).TotalMinutes, 1)
    $endTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    Write-Host ""
    if ($exitCode -eq 0) {
        Write-Host "  [DONE] Completed in $elapsed min" -ForegroundColor Green
        Add-Content -Path $logFile -Value "[$endTime] RPA MANUAL DONE ($($elapsed)min)"
    } else {
        Write-Host "  [WARN] Finished with exit code $exitCode ($elapsed min)" -ForegroundColor Yellow
        Add-Content -Path $logFile -Value "[$endTime] RPA MANUAL WARN (exit=$exitCode)"
    }
} catch {
    Write-Host "  [ERROR] $_" -ForegroundColor Red
    $errTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logFile -Value "[$errTime] RPA MANUAL ERROR: $_"
}

Write-Host ""
Write-Host "  This window will close in 10 seconds..." -ForegroundColor DarkGray
Start-Sleep -Seconds 10
