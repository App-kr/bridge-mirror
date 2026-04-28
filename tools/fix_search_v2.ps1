$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== [1] NOT_CONTENT_INDEXED via attrib +I (correct flag) ==="
# +I = Not Content Indexed for fast searching
# attrib does not support recursive +I directly - use cmd /c attrib with /S
$cmdResult = & cmd /c "attrib +I `"Q:\Claudework`" /S /D 2>&1"
$cmdResult | Select-Object -First 5
Write-Host "  Applied +I (NOT_CONTENT_INDEXED) recursively"

Write-Host ""
Write-Host "=== [2] WSearch service state ==="
$svc = Get-Service WSearch
Write-Host ("  Status: {0}, StartType: {1}" -f $svc.Status, $svc.StartType)

if ($svc.Status -eq 'Running') {
    Write-Host "  Stopping WSearch..."
    Stop-Service WSearch -Force
    Start-Sleep -Seconds 2
}
$svc = Get-Service WSearch
Write-Host ("  After stop: Status={0}" -f $svc.Status)

Write-Host ""
Write-Host "=== [3] Setting startup to Manual ==="
try {
    Set-Service -Name WSearch -StartupType Manual
    $svc = Get-Service WSearch
    Write-Host ("  StartType now: {0}" -f $svc.StartType)
} catch {
    Write-Host ("  ERROR: {0}" -f $_.Exception.Message)
    Write-Host "  (May need admin privileges)"
}

Write-Host ""
Write-Host "=== [4] System metrics (final) ==="
$os = Get-CimInstance Win32_OperatingSystem
$used = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB, 1)
$total = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
Write-Host ("  RAM: {0} GB / {1} GB ({2}%)" -f $used, $total, [math]::Round($used/$total*100,1))

$cpu = (Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 3).CounterSamples
$cpuAvg = [math]::Round(($cpu | Measure-Object CookedValue -Average).Average, 1)
Write-Host ("  CPU avg: {0}%" -f $cpuAvg)

$disk = (Get-Counter '\PhysicalDisk(_Total)\% Disk Time' -SampleInterval 1 -MaxSamples 3).CounterSamples
$diskAvg = [math]::Round(($disk | Measure-Object CookedValue -Average).Average, 1)
Write-Host ("  Disk %: {0}" -f $diskAvg)

Write-Host ""
Write-Host "=== [5] Top CPU now (5s window) ==="
$snap1 = Get-Process | Select-Object Id, ProcessName, @{N='CPU';E={$_.CPU}}
Start-Sleep -Seconds 5
$snap2 = Get-Process | Select-Object Id, ProcessName, @{N='CPU';E={$_.CPU}}
$diff = @()
foreach ($s2 in $snap2) {
    $s1 = $snap1 | Where-Object { $_.Id -eq $s2.Id }
    if ($s1 -and $s2.CPU -and $s1.CPU) {
        $delta = $s2.CPU - $s1.CPU
        if ($delta -gt 0.05) {
            $diff += [PSCustomObject]@{
                Name = $s2.ProcessName
                Id = $s2.Id
                CPU_5s = [math]::Round($delta, 2)
            }
        }
    }
}
$diff | Sort-Object CPU_5s -Descending | Select-Object -First 5 | Format-Table -AutoSize
