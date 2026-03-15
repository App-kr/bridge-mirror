chcp 65001 | Out-Null
$ProjectRoot = "Q:\Claudework\bridge base"
$PythonExe   = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe"
$LogFile     = "$ProjectRoot\logs\scheduler.log"
$Timestamp   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LogFile -Value "[$Timestamp] SCHED START" -Encoding UTF8
Set-Location $ProjectRoot
try {
    & $PythonExe "craigslist_auto_rpa.py" "--headless" "--limit" "10" 2>&1 | Out-Null
    $exitCode = $LASTEXITCODE
    $endTime  = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "[$endTime] SCHED DONE exit=$exitCode" -Encoding UTF8
} catch {
    Add-Content -Path $LogFile -Value "[(Get-Date -Format 'HH:mm:ss')] SCHED ERR: $_" -Encoding UTF8
}
