# 불필요 스케줄 태스크 삭제 스크립트
$targets = @('CreateAllJunctions', 'BridgeDetachTest001')

foreach ($name in $targets) {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($task) {
        Unregister-ScheduledTask -TaskName $name -Confirm:$false
        Write-Host "DELETED: $name"
    } else {
        Write-Host "NOT_FOUND: $name"
    }
}

# 결과 확인
Write-Host "=== 남은 Bridge 태스크 ==="
Get-ScheduledTask | Where-Object { $_.TaskName -like 'Bridge*' -or $_.TaskName -like 'Create*Junction*' } | Select-Object TaskName, State
