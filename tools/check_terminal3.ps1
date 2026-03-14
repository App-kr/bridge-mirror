# winget으로 설치된 터미널 관련 도구 확인
Write-Host "=== winget 설치 목록 (터미널/그래프 관련) ==="
winget list 2>$null | Select-String -Pattern 'posh|starship|terminal|btop|bottom|bpytop|gtop|monitor|glances|neofetch|fastfetch|winfetch' -CaseSensitive:$false

Write-Host "`n=== winget 전체 목록 (최근) ==="
winget list 2>$null | Select-Object -First 40

Write-Host "`n=== AppData Local Programs 확인 ==="
Get-ChildItem "$env:LOCALAPPDATA\Programs" -Directory -ErrorAction SilentlyContinue | Select-Object Name

Write-Host "`n=== oh-my-posh 바이너리 검색 ==="
@(
    "$env:LOCALAPPDATA\Programs\oh-my-posh",
    "$env:USERPROFILE\AppData\Local\Programs\oh-my-posh",
    "C:\Program Files\oh-my-posh",
    "$env:USERPROFILE\.local\bin"
) | ForEach-Object {
    if (Test-Path $_) { Write-Host "FOUND: $_"; Get-ChildItem $_ | Select-Object Name }
}

Write-Host "`n=== 레지스트리 시작프로그램 HKCU Run 전체 ==="
Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" | Format-List

Write-Host "`n=== 사용자 Startup 폴더 내용 ==="
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup" | ForEach-Object {
    Write-Host "$($_.Name)"
    if ($_.Extension -eq '.lnk') {
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($_.FullName)
        Write-Host "  -> $($shortcut.TargetPath) $($shortcut.Arguments)"
    }
}
