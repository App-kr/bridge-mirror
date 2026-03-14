Write-Host "=== BridgeOverlay 태스크 전체 ==="
$t = Get-ScheduledTask -TaskName 'BridgeOverlay_d8edeea9' -ErrorAction SilentlyContinue
if ($t) {
    Write-Host "State: $($t.State)"
    Write-Host "--- Actions ---"
    $t.Actions | ForEach-Object { Write-Host "Execute: $($_.Execute)  Args: $($_.Arguments)" }
    Write-Host "--- Triggers ---"
    $t.Triggers | ForEach-Object { Write-Host "Type: $($_.CimClass.CimClassName)  Delay: $($_.Delay)  Start: $($_.StartBoundary)" }
    $info = Get-ScheduledTaskInfo -TaskName 'BridgeOverlay_d8edeea9'
    Write-Host "LastRun: $($info.LastRunTime) | LastResult: $($info.LastTaskResult) | Next: $($info.NextRunTime)"
} else {
    Write-Host "NOT FOUND"
}

Write-Host "`n=== FindAgent 폴더 ==="
Get-ChildItem "C:\KED\FindAgent" -ErrorAction SilentlyContinue | Select-Object Name, Extension, Length

Write-Host "`n=== 최근 실행된 프로세스 중 오류 (이벤트 ID 1000/1001) ==="
Get-WinEvent -LogName Application -ErrorAction SilentlyContinue |
    Where-Object { ($_.Id -eq 1000 -or $_.Id -eq 1001) -and $_.TimeCreated -gt (Get-Date).AddDays(-2) } |
    Select-Object TimeCreated, Id, @{N='Source';E={$_.ProviderName}}, @{N='App';E={$_.Properties[0].Value}} |
    Sort-Object TimeCreated -Descending | Select-Object -First 10 | Format-Table -AutoSize

Write-Host "`n=== 모든 로그온 트리거 태스크 목록 ==="
Get-ScheduledTask -ErrorAction SilentlyContinue | ForEach-Object {
    $tn = $_.TaskName
    $_.Triggers | ForEach-Object {
        if ($_.CimClass.CimClassName -like '*Logon*') {
            $action = (Get-ScheduledTask -TaskName $tn -ErrorAction SilentlyContinue).Actions | Select-Object -First 1
            Write-Host "LOGON-TASK: $tn | $($action.Execute) $($action.Arguments)"
        }
    }
}
