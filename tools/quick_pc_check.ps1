$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== System metrics (3s avg) ==="
$cpu = (Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 3).CounterSamples
$cpuAvg = [math]::Round(($cpu | Measure-Object CookedValue -Average).Average, 1)
$disk = (Get-Counter '\PhysicalDisk(_Total)\% Disk Time' -SampleInterval 1 -MaxSamples 3).CounterSamples
$diskAvg = [math]::Round(($disk | Measure-Object CookedValue -Average).Average, 1)
$os = Get-CimInstance Win32_OperatingSystem
$used = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB, 1)
$total = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
Write-Host ("  CPU: {0}%   Disk: {1}%   RAM: {2}/{3} GB" -f $cpuAvg, $diskAvg, $used, $total)

Write-Host ""
Write-Host "=== TOP 10 CPU consumers (delta over 5s) ==="
$snap1 = Get-Process | Select-Object Id, ProcessName, CPU, WorkingSet64
Start-Sleep -Seconds 5
$snap2 = Get-Process | Select-Object Id, ProcessName, CPU, WorkingSet64
$diff = @()
foreach ($s2 in $snap2) {
    $s1 = $snap1 | Where-Object { $_.Id -eq $s2.Id }
    if ($s1 -and $s2.CPU -ne $null -and $s1.CPU -ne $null) {
        $delta = $s2.CPU - $s1.CPU
        if ($delta -gt 0.1) {
            $diff += [PSCustomObject]@{
                Name = $s2.ProcessName
                Id = $s2.Id
                CPU_5s = [math]::Round($delta, 2)
                RAM_MB = [math]::Round($s2.WorkingSet64/1MB, 1)
            }
        }
    }
}
$diff | Sort-Object CPU_5s -Descending | Select-Object -First 10 | Format-Table -AutoSize

Write-Host ""
Write-Host "=== TOP 5 RAM ==="
Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 5 |
    Select-Object Name, Id, @{N='RAM_MB';E={[math]::Round($_.WorkingSet/1MB,1)}} |
    Format-Table -AutoSize

Write-Host ""
Write-Host "=== TOP IO recently (delta) ==="
$diff2 = @()
foreach ($s2 in $snap2) {
    $proc1 = Get-Process -Id $s2.Id -ErrorAction SilentlyContinue
    if ($proc1) {
        $diff2 += [PSCustomObject]@{
            Name = $proc1.ProcessName
            Id = $proc1.Id
            IO_Total = ($proc1.IO_ReadOperationCount + $proc1.IO_WriteOperationCount + $proc1.IO_OtherOperationCount)
        }
    }
}
$diff2 | Sort-Object IO_Total -Descending | Select-Object -First 8 | Format-Table -AutoSize

Write-Host ""
Write-Host "=== Antigravity status ==="
$ag = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '*Antigravity*' }
if ($ag) {
    $sumRam = ($ag | Measure-Object WorkingSetSize -Sum).Sum / 1MB
    Write-Host ("  Processes: {0}  Total RAM: {1} MB" -f $ag.Count, [math]::Round($sumRam,1))
}

Write-Host ""
Write-Host "=== Windows Update / Defender activity ==="
@('TiWorker','MsMpEng','wuauclt','MoUsoCoreWorker','MsSense','SecurityHealthService') | ForEach-Object {
    $p = Get-Process -Name $_ -ErrorAction SilentlyContinue
    if ($p) {
        $p | ForEach-Object {
            Write-Host ("  {0}(PID {1})  RAM={2}MB" -f $_.ProcessName, $_.Id, [math]::Round($_.WorkingSet/1MB,1))
        }
    }
}
