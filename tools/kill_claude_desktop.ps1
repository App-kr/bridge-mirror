$ErrorActionPreference = 'Continue'

Write-Host "=== Killing Anthropic Claude desktop app (메신저) ==="
Write-Host "보호 대상 (절대 안 죽임):"
Write-Host "  - Claude Code CLI (AppData\Roaming\Claude\claude-code\*)"
Write-Host "  - Antigravity"
Write-Host "  - 사용자 브라우저/게임"
Write-Host ""

$killed = 0
Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -like '*WindowsApps\Claude_*\app\Claude.exe'
} | ForEach-Object {
    Write-Host ("  KILL PID={0} {1}" -f $_.ProcessId, $_.ExecutablePath)
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    $killed++
}
Write-Host "`nKilled: $killed processes"

# 잔존 확인
Start-Sleep -Seconds 2
$remaining = Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -like '*WindowsApps\Claude_*\app\Claude.exe'
}
if ($remaining) {
    Write-Host "WARN: $($remaining.Count) instance(s) still running"
    $remaining | ForEach-Object {
        Write-Host "  Force-kill PID=$($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "OK: All Claude desktop instances killed"
}

# 보호 대상 확인
Write-Host "`n=== 보호 대상 정상 동작 중 (확인) ==="
$cliCount = (Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -like '*claude-code*'
}).Count
$antiCount = (Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -like '*Antigravity*'
}).Count
Write-Host "  Claude Code CLI 인스턴스: $cliCount"
Write-Host "  Antigravity 인스턴스: $antiCount"

Write-Host "`n=== 종료 후 spawn rate (10s) ==="
$counts = @{}
$total = 0
$end = (Get-Date).AddSeconds(10)
$seen = @{}
while ((Get-Date) -lt $end) {
    Get-CimInstance Win32_Process -Filter "Name='cmd.exe' OR Name='powershell.exe' OR Name='conhost.exe' OR Name='git.exe' OR Name='gh.exe'" | ForEach-Object {
        if (-not $seen.ContainsKey($_.ProcessId)) {
            $seen[$_.ProcessId] = $true
            $total++
            $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.ParentProcessId)"
            $key = if ($parent) { $parent.Name } else { 'GONE' }
            if (-not $counts.ContainsKey($key)) { $counts[$key] = 0 }
            $counts[$key]++
        }
    }
    Start-Sleep -Milliseconds 250
}
Write-Host "  총 spawn (10s): $total ($([math]::Round($total / 10.0, 2))/sec)"
$counts.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 5 | ForEach-Object {
    Write-Host ("    {0,3}x  {1}" -f $_.Value, $_.Key)
}
