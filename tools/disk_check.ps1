# 1. 드라이브 목록
Write-Host "=== 드라이브 현황 ===" -ForegroundColor Cyan
Get-PSDrive -PSProvider FileSystem | ForEach-Object {
    $total = $_.Used + $_.Free
    $usedGB = [math]::Round($_.Used/1GB, 1)
    $freeGB = [math]::Round($_.Free/1GB, 1)
    $totalGB = [math]::Round($total/1GB, 1)
    Write-Host "$($_.Name): 사용 ${usedGB}GB / 전체 ${totalGB}GB / 여유 ${freeGB}GB"
}

# 2. 물리 디스크 상태 (SMART)
Write-Host "`n=== 디스크 SMART 상태 ===" -ForegroundColor Cyan
Get-PhysicalDisk | ForEach-Object {
    Write-Host "[$($_.FriendlyName)] 상태: $($_.HealthStatus) | 미디어: $($_.MediaType) | 크기: $([math]::Round($_.Size/1GB,0))GB"
}

# 3. 볼륨 상태
Write-Host "`n=== 볼륨 상태 ===" -ForegroundColor Cyan
Get-Volume | Where-Object { $_.DriveLetter } | ForEach-Object {
    Write-Host "$($_.DriveLetter): $($_.FileSystemLabel) | 상태: $($_.HealthStatus) | FS: $($_.FileSystem)"
}
