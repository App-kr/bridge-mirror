# Q:\Claudework\bridge 구 디렉토리 상세 점검
Write-Host "=== Q:\Claudework\bridge 내 확장자 없는 파일 ==="
Get-ChildItem "Q:\Claudework\bridge" -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -eq '' -and $_.PSIsContainer -eq $false } |
    Select-Object FullName, Length, LastWriteTime

Write-Host "`n=== Q:\Claudework\bridge 전체 구조 ==="
Get-ChildItem "Q:\Claudework\bridge" -Recurse -ErrorAction SilentlyContinue |
    Select-Object FullName, Extension, LastWriteTime | Sort-Object LastWriteTime -Descending

Write-Host "`n=== Q:\Claudework 루트 파일 중 .vbs 또는 확장자 없는 것 ==="
Get-ChildItem "Q:\Claudework" -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -eq '' -or $_.Extension -match 'vbs|vbe|js|jse|wsf' } |
    Select-Object Name, Extension, FullName, LastWriteTime

Write-Host "`n=== HKCU/HKLM Run에서 bridge 포함 항목 ==="
@("HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
  "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
  "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
  "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce") | ForEach-Object {
    $k = Get-ItemProperty $_ -ErrorAction SilentlyContinue
    if ($k) {
        $k.PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' -and $_.Value -match 'bridge' } | ForEach-Object {
            Write-Host "KEY: $_ | Name: $($_.Name) | Value: $($_.Value)"
        }
    }
}

Write-Host "=== wscript/cscript process ==="
Get-Process | Where-Object { $_.Name -match 'wscript|cscript' } | Select-Object Id, Name, Path
