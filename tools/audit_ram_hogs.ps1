$ErrorActionPreference = 'SilentlyContinue'

Write-Host "=== A) RAM 사용 상위 30개 프로세스 ==="
Get-Process | Sort-Object -Property WorkingSet -Descending |
    Select-Object -First 30 |
    ForEach-Object {
        [PSCustomObject]@{
            Name    = $_.ProcessName
            PID     = $_.Id
            RAM_MB  = [math]::Round($_.WorkingSet / 1MB, 1)
            Path    = $_.Path
            Started = $_.StartTime
        }
    } | Format-Table -AutoSize -Wrap

Write-Host "`n=== B) BRIDGE 관련 정상 daemon 확인 ==="
$brigeProcs = Get-Process | Where-Object {
    $_.Path -like '*Claudework*' -or
    $_.MainWindowTitle -match 'BRIDGE|bridge|api_server|wealth' -or
    $_.ProcessName -in @('pythonw','python','node','tg_approval_daemon')
}
$brigeProcs | Select-Object ProcessName, Id, @{N='RAM_MB';E={[math]::Round($_.WorkingSet/1MB,1)}}, Path |
    Sort-Object RAM_MB -Descending | Format-Table -AutoSize -Wrap

Write-Host "`n=== C) 부모-자식 트리 (의심 프로세스 추적용) ==="
Get-CimInstance Win32_Process | ForEach-Object {
    [PSCustomObject]@{
        PID       = $_.ProcessId
        ParentPID = $_.ParentProcessId
        Name      = $_.Name
        RAM_MB    = [math]::Round($_.WorkingSetSize/1MB, 1)
        CmdLine   = if ($_.CommandLine) { $_.CommandLine.Substring(0, [Math]::Min(150, $_.CommandLine.Length)) } else { '' }
    }
} | Where-Object { $_.RAM_MB -gt 50 } | Sort-Object RAM_MB -Descending |
    Select-Object -First 25 | Format-Table -AutoSize -Wrap

Write-Host "`n=== D) 시스템 메모리 ==="
$os = Get-CimInstance Win32_OperatingSystem
$totalGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
$freeGB  = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
$usedGB  = [math]::Round($totalGB - $freeGB, 1)
$pct     = [math]::Round(($usedGB / $totalGB) * 100, 1)
Write-Host "Total: ${totalGB}GB | Used: ${usedGB}GB ($pct%) | Free: ${freeGB}GB"

Write-Host "`n=== E) 의심 위치 실행 (AppData\Roaming, Temp 등) ==="
Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -match 'AppData\\Roaming\\|\\Temp\\|\\Recycle' -and
    $_.ExecutablePath -notmatch 'Microsoft|Google|Discord|Spotify|GitHub|nvm'
} | Select-Object ProcessId, Name, ExecutablePath, @{N='RAM_MB';E={[math]::Round($_.WorkingSetSize/1MB,1)}} |
    Format-Table -AutoSize -Wrap
