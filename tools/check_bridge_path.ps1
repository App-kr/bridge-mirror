# "Q:\Claudework\bridge" 경로 존재 여부 확인
Write-Host "=== Q:\Claudework\bridge 존재 여부 ==="
if (Test-Path "Q:\Claudework\bridge") {
    $item = Get-Item "Q:\Claudework\bridge"
    Write-Host "EXISTS: $($item.FullName)"
    Write-Host "Attributes: $($item.Attributes)"
    # Junction/Symlink 여부
    if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        Write-Host "TYPE: Junction/SymLink"
        cmd /c dir "Q:\Claudework" | Select-String "bridge"
    } else {
        Write-Host "TYPE: Regular Directory/File"
    }
} else {
    Write-Host "NOT EXISTS"
}

Write-Host "`n=== Q:\Claudework 폴더 목록 ==="
Get-ChildItem "Q:\Claudework" | Select-Object Name, Attributes, LastWriteTime

Write-Host "`n=== wscript.exe를 호출하는 .lnk 파일 검색 ==="
# 전체 사용자 Startup
Get-ChildItem "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  ProgramData Startup: $($_.Name)"
}

Write-Host "`n=== HKCU Run에 wscript 관련 있는지 ==="
Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue |
    Select-Object * -ExcludeProperty PS* | Format-List

Write-Host "`n=== Audio 관련 파일에서 bridge 경로 비쿼트 사용 여부 ==="
Get-Content "Q:\Claudework\bridge base\tools\audio_switcher_run.vbs" -ErrorAction SilentlyContinue
Get-Content "Q:\Headset\audio-toggle.ahk" -ErrorAction SilentlyContinue | Select-String -Pattern 'wscript|bridge base|Run.*bridge' -CaseSensitive:0
