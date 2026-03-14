# backup_daemon.py 스케줄 작업 찾기
$tasks = Get-ScheduledTask -ErrorAction SilentlyContinue
foreach ($t in $tasks) {
    $actions = $t.Actions
    foreach ($a in $actions) {
        if ($a.Execute -like "*backup_daemon*" -or $a.Arguments -like "*backup_daemon*") {
            Write-Host "발견: $($t.TaskPath)$($t.TaskName)"
            Write-Host "  실행: $($a.Execute) $($a.Arguments)"
            Write-Host "  상태: $($t.State)"
        }
    }
}
Write-Host "검색 완료"
