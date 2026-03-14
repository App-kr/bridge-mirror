# 터미널 상태그래프 관련 설치 도구 점검

Write-Host "=== PowerShell 프로필 확인 ==="
$profiles = @(
    $PROFILE.CurrentUserCurrentHost,
    $PROFILE.CurrentUserAllHosts,
    $PROFILE.AllUsersCurrentHost,
    $PROFILE.AllUsersAllHosts
)
foreach ($p in $profiles) {
    if (Test-Path $p) {
        Write-Host "EXISTS: $p"
        Get-Content $p | Select-Object -First 30
        Write-Host "---"
    } else {
        Write-Host "NOT_EXISTS: $p"
    }
}

Write-Host "`n=== Oh My Posh 설치 여부 ==="
Get-Command oh-my-posh -ErrorAction SilentlyContinue | Select-Object Name, Source

Write-Host "`n=== Starship 설치 여부 ==="
Get-Command starship -ErrorAction SilentlyContinue | Select-Object Name, Source

Write-Host "`n=== btop/htop/gtop 설치 여부 ==="
@('btop','htop','gtop','bpytop','ctop') | ForEach-Object {
    $cmd = Get-Command $_ -ErrorAction SilentlyContinue
    if ($cmd) { Write-Host "FOUND: $_ -> $($cmd.Source)" }
}

Write-Host "`n=== Windows Terminal 설정 경로 ==="
$wtSettings = "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json"
if (Test-Path $wtSettings) {
    Write-Host "EXISTS: $wtSettings"
    $content = Get-Content $wtSettings -Raw | ConvertFrom-Json
    Write-Host "startupActions: $($content.startupActions)"
    $content.profiles.defaults | ConvertTo-Json -Depth 3
} else {
    Write-Host "NOT_FOUND: $wtSettings"
}

Write-Host "`n=== npm global 패키지 (터미널 관련) ==="
npm list -g --depth=0 2>$null | Select-String -Pattern 'terminal|monitor|status|graph|prompt|posh' -CaseSensitive:$false

Write-Host "`n=== Python 설치 패키지 (터미널 관련) ==="
pip list 2>$null | Select-String -Pattern 'rich|textual|urwid|blessed|curses|tqdm|alive|progress' -CaseSensitive:$false
