# 터미널 추가 점검

Write-Host "=== PowerShell 7 프로필 ==="
$ps7profile = "$env:USERPROFILE\Documents\PowerShell\Microsoft.PowerShell_profile.ps1"
if (Test-Path $ps7profile) {
    Write-Host "EXISTS: $ps7profile"
    Get-Content $ps7profile
} else {
    Write-Host "NOT_EXISTS: $ps7profile"
}

Write-Host "`n=== Windows Terminal 패키지 경로들 ==="
Get-ChildItem "$env:LOCALAPPDATA\Packages" -Directory | Where-Object { $_.Name -like '*Terminal*' -or $_.Name -like '*wt*' } | Select-Object Name

Write-Host "`n=== bash 시작 파일 ==="
@("$env:USERPROFILE\.bashrc", "$env:USERPROFILE\.bash_profile", "$env:USERPROFILE\.profile") | ForEach-Object {
    if (Test-Path $_) {
        Write-Host "EXISTS: $_"
        Get-Content $_
    }
}

Write-Host "`n=== 최근 설치된 프로그램 (1주일 이내) ==="
Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\* |
    Where-Object { $_.InstallDate -gt (Get-Date).AddDays(-14).ToString('yyyyMMdd') } |
    Select-Object DisplayName, InstallDate |
    Sort-Object InstallDate -Descending | Select-Object -First 15

Write-Host "`n=== Chocolatey 설치 패키지 ==="
if (Get-Command choco -ErrorAction SilentlyContinue) {
    choco list --local-only 2>$null | Select-String -Pattern 'terminal|monitor|status|graph|prompt|posh|btop|htop|bottom|bpytop' -CaseSensitive:$false
}

Write-Host "`n=== Scoop 설치 패키지 ==="
if (Get-Command scoop -ErrorAction SilentlyContinue) {
    scoop list 2>$null | Select-String -Pattern 'terminal|monitor|status|graph|prompt|posh|btop|htop|bottom' -CaseSensitive:$false
}

Write-Host "`n=== 환경변수 PATH에서 터미널 관련 ==="
$env:PATH -split ';' | Where-Object { $_ -match 'posh|starship|terminal|monitor' }
