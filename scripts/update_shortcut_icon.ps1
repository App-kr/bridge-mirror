# 바탕화면 단축아이콘 아이콘만 업데이트
$DESKTOP  = [Environment]::GetFolderPath("Desktop")
$BASE     = "Q:\Claudework\bridge base"
$lnkPath  = "$DESKTOP\BRIDGE Craig RPA.lnk"
$icoPath  = "$BASE\images\craig_icon.ico"

if (-not (Test-Path $lnkPath)) {
    Write-Host "단축아이콘 없음 - register_task.ps1 실행 필요"
    exit 1
}

$ws  = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut($lnkPath)
$lnk.IconLocation = "$icoPath,0"
$lnk.Save()
Write-Host "단축아이콘 아이콘 업데이트 완료: $lnkPath"
Write-Host "아이콘 경로: $icoPath"
