$backupDir = "Q:\Claudework\_BACKUP"
$snapshots = Get-ChildItem -Path $backupDir -Directory |
    Where-Object { $_.Name -match '^\d{8}_\d{6}$' } |
    Sort-Object Name -Descending

Write-Host "총 스냅샷: $($snapshots.Count)개" -ForegroundColor Yellow
Write-Host "삭제 대상: $($snapshots.Count - 3)개" -ForegroundColor Red

$snapshots | Select-Object -Skip 3 | ForEach-Object {
    Remove-Item -Path $_.FullName -Recurse -Force
    Write-Host "삭제: $($_.Name)" -ForegroundColor Green
}

Write-Host ""
Write-Host "삭제 완료. 용량 재확인 중..." -ForegroundColor Cyan

Get-Volume -DriveLetter Q | Select-Object `
    @{N='드라이브';E={'Q'}},
    @{N='용량(GB)';E={[math]::Round($_.Size/1GB,1)}},
    @{N='사용(GB)';E={[math]::Round(($_.Size - $_.SizeRemaining)/1GB,1)}},
    @{N='여유(GB)';E={[math]::Round($_.SizeRemaining/1GB,1)}}
