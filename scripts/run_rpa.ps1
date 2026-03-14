# Bridge Craigslist RPA Runner
chcp 65001 > $null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$LogFile = "K:\BridgeCraig\logs\scheduler.log"
Add-Content -Path $LogFile -Value "[$Timestamp] RPA START" -Encoding UTF8
Set-Location "K:\BridgeCraig"
try {
    & python craigslist_auto_rpa.py --headless --limit 10 2>&1 | Out-Null
    $endTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "[$endTime] RPA DONE (exit=$LASTEXITCODE)" -Encoding UTF8
} catch {
    $errTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "[$errTime] RPA ERROR: $_" -Encoding UTF8
}
