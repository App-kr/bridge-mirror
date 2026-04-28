$ErrorActionPreference = 'SilentlyContinue'

Write-Host "=== A) 4-daemon 운영 상태 ==="
@('BRIDGE_FocusGuard','BRIDGE_RAMWatchdog','BRIDGE_GameModeGuardian') | ForEach-Object {
    $info = Get-ScheduledTaskInfo -TaskName $_ -ErrorAction SilentlyContinue
    if ($info) {
        Write-Host ("  {0}: lastRun={1} result={2}" -f $_, $info.LastRunTime, $info.LastTaskResult)
    } else {
        Write-Host ("  {0}: NOT REGISTERED" -f $_)
    }
}

Write-Host "`n=== B) focus_guard 프로세스 확인 ==="
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*focus_guard.py*' } |
    Select-Object ProcessId, @{N='age_min';E={[math]::Round(((Get-Date)-$_.CreationDate).TotalMinutes,1)}}, @{N='RAM';E={[math]::Round($_.WorkingSetSize/1MB,1)}} |
    Format-Table -AutoSize

Write-Host "`n=== C) game_mode_guardian 프로세스 확인 ==="
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*game_mode_guardian.py*' } |
    Select-Object ProcessId, @{N='age_min';E={[math]::Round(((Get-Date)-$_.CreationDate).TotalMinutes,1)}}, @{N='RAM';E={[math]::Round($_.WorkingSetSize/1MB,1)}} |
    Format-Table -AutoSize

Write-Host "`n=== D) ForegroundLockTimeout (Windows focus protection) ==="
$flt = (Get-ItemProperty 'HKCU:\Control Panel\Desktop' -Name 'ForegroundLockTimeout' -ErrorAction SilentlyContinue).ForegroundLockTimeout
Write-Host "  Current: $flt (decimal ms)"
Write-Host "  0 = 다른 프로세스가 자유롭게 포커스 빼앗을 수 있음"
Write-Host "  200000 = 200초 동안 사용자 창 보호"

Write-Host "`n=== E) 30초 동안 cmd/PS spawn 실시간 추적 (parent별) ==="
$seen = @{}
$culprits = @{}
$end = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $end) {
    Get-CimInstance Win32_Process -Filter "Name='cmd.exe' OR Name='powershell.exe' OR Name='conhost.exe' OR Name='git.exe' OR Name='gh.exe'" | ForEach-Object {
        if (-not $seen.ContainsKey($_.ProcessId)) {
            $seen[$_.ProcessId] = $true
            $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.ParentProcessId)"
            $pname = if ($parent) { $parent.Name } else { 'GONE' }
            $key = "$($_.Name) <- $pname"
            if (-not $culprits.ContainsKey($key)) {
                $culprits[$key] = 0
            }
            $culprits[$key]++
        }
    }
    Start-Sleep -Milliseconds 250
}

Write-Host "`n=== Top spawn patterns (30s window) ==="
$culprits.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 10 | ForEach-Object {
    Write-Host ("  {0,3}x  {1}" -f $_.Value, $_.Key)
}
Write-Host ("`nTotal new processes spawned in 30s: {0}" -f $seen.Count)
Write-Host ("Rate: {0} per second" -f [math]::Round($seen.Count / 30.0, 2))

Write-Host "`n=== F) focus_guard 최근 hidden 활동 (last 20) ==="
$logPath = "Q:\Claudework\bridge base\logs\focus_guard.jsonl"
if (Test-Path $logPath) {
    Get-Content $logPath -Tail 20 | ForEach-Object {
        try {
            $j = $_ | ConvertFrom-Json
            if ($j.event -eq 'HIDDEN_EVT' -or $j.event -eq 'HIDDEN_POLL') {
                Write-Host ("  {0} {1} pid={2} title={3}" -f $j.ts, $j.event, $j.pid, $j.title.Substring(0,[Math]::Min(50,$j.title.Length)))
            } else {
                Write-Host ("  {0} {1}" -f $j.ts, $j.event)
            }
        } catch { Write-Host "  (parse fail)" }
    }
}
