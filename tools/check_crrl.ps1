Write-Host "=== BridgeCrRL 태스크 상세 ==="
$t = Get-ScheduledTask -TaskName 'BridgeCrRL_b8d23f43' -ErrorAction SilentlyContinue
if ($t) {
    Write-Host "State: $($t.State)"
    $t.Actions | Format-List
    $t.Triggers | Format-List
    $info = Get-ScheduledTaskInfo -TaskName 'BridgeCrRL_b8d23f43' -ErrorAction SilentlyContinue
    if ($info) {
        Write-Host "LastRun: $($info.LastRunTime)"
        Write-Host "LastResult: $($info.LastTaskResult)"
        Write-Host "NextRun: $($info.NextRunTime)"
    }
} else {
    Write-Host "NOT FOUND"
}

Write-Host "`n=== BridgeOverlay_d8edeea9 태스크 상세 ==="
$t2 = Get-ScheduledTask -TaskName 'BridgeOverlay_d8edeea9' -ErrorAction SilentlyContinue
if ($t2) {
    Write-Host "State: $($t2.State)"
    $t2.Actions | Format-List
    $t2.Triggers | Format-List
    $info2 = Get-ScheduledTaskInfo -TaskName 'BridgeOverlay_d8edeea9' -ErrorAction SilentlyContinue
    if ($info2) {
        Write-Host "LastRun: $($info2.LastRunTime)"
        Write-Host "LastResult: $($info2.LastTaskResult)"
    }
}

Write-Host "`n=== 확장자 없이 실행되는 항목 탐색 ==="
# 스케줄러 전체에서 확장자 없는 실행 파일 찾기
Get-ScheduledTask -ErrorAction SilentlyContinue | ForEach-Object {
    $tn = $_.TaskName
    $_.Actions | ForEach-Object {
        $exe = $_.Execute -replace '"',''
        if ($exe -and ($exe -notmatch '\.\w+$') -and ($exe -notmatch '^$')) {
            Write-Host "Task: $tn | Execute(no-ext): $exe | Args: $($_.Arguments)"
        }
    }
}

Write-Host "`n=== overlay_state.json 존재 여부 ==="
$f = "Q:\Claudework\bridge base\overlay_state.json"
if (Test-Path $f) {
    Write-Host "EXISTS:"
    Get-Content $f
} else {
    Write-Host "NOT EXISTS"
}
