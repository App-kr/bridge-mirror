# 2026-04-27 - Lingering process cleanup (user-approved)
$ErrorActionPreference = 'Continue'

Write-Host "=== 1) Memory before ==="
$os1 = Get-CimInstance Win32_OperatingSystem
$used1 = [math]::Round(($os1.TotalVisibleMemorySize - $os1.FreePhysicalMemory) / 1MB, 1)
Write-Host "Used: ${used1} GB"

Write-Host "`n=== 2) Kill bridge_ads Next.js dev server ==="
$adsKilled = 0
Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -match 'bridge_ads' -and $_.Name -eq 'node.exe'
} | ForEach-Object {
    Write-Host ("KILL bridge_ads PID={0} RAM={1}MB" -f $_.ProcessId, [math]::Round($_.WorkingSetSize/1MB, 1))
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    $adsKilled++
}
Write-Host "bridge_ads killed: $adsKilled"

Write-Host "`n=== 3) Lingering RPA/blog/mail daemon scan ==="
$lingerPatterns = @(
    'craigslist_auto_rpa',
    'rpa_overlay',
    'inject_draft',
    'tg_send',
    'mail_send',
    'auto_post_blog',
    'send_introduce_mail',
    'matjokdo'
)
$found = 0
Get-CimInstance Win32_Process | ForEach-Object {
    $cmd = $_.CommandLine
    if (-not $cmd) { return }
    foreach ($p in $lingerPatterns) {
        if ($cmd -match $p) {
            Write-Host ("  CANDIDATE PID={0} {1} | {2}MB | match={3}" -f $_.ProcessId, $_.Name,
                [math]::Round($_.WorkingSetSize/1MB,1), $p)
            $found++
            break
        }
    }
}
if ($found -eq 0) { Write-Host "  (none)" }

Write-Host "`n=== 4) Long-running (>1h) high-RAM (>200MB) suspects ==="
$now = Get-Date
$exclude = @('claude','Discord','chrome','msedge','TslGame','dwm','explorer','SearchIndexer','MsMpEng','svchost','MemoryCompression','Code','Claude','spotify','KakaoTalk','OUTLOOK','Notion','Slack','Teams')
Get-Process | Where-Object {
    $_.StartTime -and
    ($now - $_.StartTime).TotalHours -gt 1 -and
    ($_.WorkingSet / 1MB) -gt 200 -and
    $_.ProcessName -notin $exclude -and
    $_.Path -notmatch 'WindowsApps|Microsoft\\|Program Files\\Common'
} | Select-Object ProcessName, Id,
    @{N='RAM_MB';E={[math]::Round($_.WorkingSet/1MB,1)}},
    @{N='Hours';E={[math]::Round(($now - $_.StartTime).TotalHours,1)}},
    Path |
    Sort-Object RAM_MB -Descending | Format-Table -AutoSize -Wrap

Write-Host "`n=== 5) Memory after ==="
Start-Sleep -Seconds 2
$os2 = Get-CimInstance Win32_OperatingSystem
$used2 = [math]::Round(($os2.TotalVisibleMemorySize - $os2.FreePhysicalMemory) / 1MB, 1)
$totalGB = [math]::Round($os2.TotalVisibleMemorySize / 1MB, 1)
$pct2 = [math]::Round(($used2 / $totalGB) * 100, 1)
$delta = [math]::Round($used1 - $used2, 1)
Write-Host "Used: ${used2} GB ($pct2%) | Reclaimed: ${delta} GB"
