$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Memory Before ==="
$os1 = Get-CimInstance Win32_OperatingSystem
$used1 = [math]::Round(($os1.TotalVisibleMemorySize - $os1.FreePhysicalMemory) / 1MB, 1)
Write-Host ("  RAM: {0} GB" -f $used1)

# 사용자 작업 도구 (보호)
$PROTECT_NAMES = @(
    'TslGame','Overwatch','LeagueClient','Valorant','rl','csgo','cs2',
    'claude','Antigravity','Discord','chrome','msedge','Spotify',
    'KakaoTalk','dwm','explorer','svchost','MsMpEng','SearchHost',
    'ApplicationFrameHost','SystemSettings','ShellExperienceHost',
    'StartMenuExperienceHost','SecurityHealthHost','RuntimeBroker',
    'pythonw','node','TextInputHost','conhost','ctfmon','sihost',
    'fontdrvhost','LockApp','LogonUI','smss','csrss','wininit','services',
    'lsass','winlogon','dllhost','spoolsv','SearchIndexer','wuauclt',
    'NVIDIA','GoogleDriveFS','OneDrive','AdobeIPCBroker','CCXProcess',
    'AdobeNotificationClient','Code','Cursor','Tailscale','tailscaled',
    'SecurityHealthService','Memory Compression','System','Idle','Registry'
)

# 정리 대상 (게임 중 죽여도 OK)
$KILL_PATTERNS = @(
    @{ name='bridge_ads node'; cmd_match='bridge_ads.*next' },
    @{ name='wealth_manager idle'; cmd_match='wealth_manager.*next' },
    @{ name='chromedriver'; name_match='chromedriver' },
    @{ name='geckodriver'; name_match='geckodriver' },
    @{ name='msedgedriver'; name_match='msedgedriver' },
    @{ name='craigslist RPA'; cmd_match='craigslist_auto_rpa' },
    @{ name='inject_draft blog'; cmd_match='inject_draft' },
    @{ name='auto_post_blog'; cmd_match='auto_post_blog' },
    @{ name='send_introduce_mail'; cmd_match='send_introduce_mail' },
    @{ name='matjokdo run_daily'; cmd_match='matjokdo.*run_daily' },
    @{ name='ClaudeBlog publish lingering'; cmd_match='ClaudeBlog.*main\.py' }
)

Write-Host ""
Write-Host "=== Killing lingering processes (game protection) ==="
$killed = 0
$reclaimed = 0

foreach ($pat in $KILL_PATTERNS) {
    $procs = @()
    if ($pat.cmd_match) {
        $procs = Get-CimInstance Win32_Process | Where-Object {
            $_.CommandLine -match $pat.cmd_match -and
            $_.Name -notin $PROTECT_NAMES
        }
    }
    if ($pat.name_match) {
        $procs = Get-CimInstance Win32_Process | Where-Object {
            $_.Name -match $pat.name_match
        }
    }
    foreach ($p in $procs) {
        $ram = [math]::Round($p.WorkingSetSize/1MB, 1)
        $age = [math]::Round(((Get-Date)-$p.CreationDate).TotalMinutes, 1)
        Write-Host ("  KILL [{0}] PID={1} RAM={2}MB age={3}m" -f $pat.name, $p.ProcessId, $ram, $age)
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        $killed++
        $reclaimed += $ram
    }
}

Write-Host ""
Write-Host ("Killed {0} processes, reclaim target: {1} MB" -f $killed, [math]::Round($reclaimed, 1))

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "=== Memory After ==="
$os2 = Get-CimInstance Win32_OperatingSystem
$used2 = [math]::Round(($os2.TotalVisibleMemorySize - $os2.FreePhysicalMemory) / 1MB, 1)
$delta = [math]::Round($used1 - $used2, 1)
Write-Host ("  RAM: {0} GB (reclaimed: {1} GB)" -f $used2, $delta)

Write-Host ""
Write-Host "=== Game + user apps preserved ==="
@('TslGame','claude','Antigravity','Discord','chrome') | ForEach-Object {
    $p = Get-Process -Name $_ -ErrorAction SilentlyContinue
    if ($p) {
        $sumRam = [math]::Round((($p | Measure-Object WorkingSet -Sum).Sum)/1MB, 1)
        Write-Host ("  {0}: {1} instances, {2} MB" -f $_, $p.Count, $sumRam)
    }
}

Write-Host ""
Write-Host "=== Top 5 RAM consumers (current) ==="
Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 5 |
    Select-Object Name, Id, @{N='RAM_MB';E={[math]::Round($_.WorkingSet/1MB,1)}} |
    Format-Table -AutoSize
