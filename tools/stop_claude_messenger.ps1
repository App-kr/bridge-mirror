$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== 1) Killing Anthropic Claude desktop app instances ==="
$killed = 0
$totalRam = 0
Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -like '*WindowsApps\Claude_*\app\Claude.exe'
} | ForEach-Object {
    $ram = [math]::Round($_.WorkingSetSize/1MB, 1)
    $totalRam += $ram
    Write-Host ("  KILL PID={0} RAM={1}MB" -f $_.ProcessId, $ram)
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    $killed++
}
Start-Sleep -Seconds 2

# 잔존 강제 재 kill
$still = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '*WindowsApps\Claude_*' }
if ($still) {
    foreach ($p in $still) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-Host ("  Force re-kill: {0}" -f $still.Count)
}

Write-Host ("`nKilled: {0} processes, ~{1}MB freed" -f $killed, [math]::Round($totalRam, 1))

Write-Host ""
Write-Host "=== 2) Disable Claude desktop autostart ==="
# StartupApproved\Run / StartupApproved\StartupFolder
@(
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run',
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder'
) | ForEach-Object {
    $key = $_
    $items = Get-ItemProperty $key -ErrorAction SilentlyContinue
    if ($items) {
        $items.PSObject.Properties | Where-Object {
            $_.Name -like '*Claude*' -or $_.Name -like '*Anthropic*'
        } | ForEach-Object {
            $val = $_.Value
            if ($val -is [byte[]] -and $val.Length -ge 1) {
                # 첫 바이트 03 = disabled
                if ($val[0] -eq 2) {
                    $val[0] = 3
                    Set-ItemProperty $key -Name $_.Name -Value $val -Type Binary
                    Write-Host ("  DISABLED autostart: {0} ({1})" -f $_.Name, $key)
                } else {
                    Write-Host ("  already-disabled: {0}" -f $_.Name)
                }
            }
        }
    }
}

# 사용자 시작프로그램 폴더의 Claude .lnk 도 검사
$startup = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
Get-ChildItem $startup -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -like '*Claude*' -or $_.Name -like '*Anthropic*'
} | ForEach-Object {
    $bak = $_.FullName + ".disabled"
    Move-Item $_.FullName $bak -Force
    Write-Host ("  RENAMED to .disabled: {0}" -f $_.FullName)
}

Write-Host ""
Write-Host "=== 3) Final verification ==="
$still = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '*WindowsApps\Claude_*' }
if ($still) {
    Write-Host ("  WARN: {0} instances still running" -f $still.Count)
} else {
    Write-Host "  OK: zero Claude desktop instances"
}

# Memory state
$os = Get-CimInstance Win32_OperatingSystem
$used = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB, 1)
$total = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
Write-Host ("  RAM: {0} GB / {1} GB ({2}%)" -f $used, $total, [math]::Round($used/$total*100, 1))
