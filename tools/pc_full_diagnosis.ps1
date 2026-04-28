$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=================================================="
Write-Host "PC FULL DIAGNOSIS - 60s window"
Write-Host "=================================================="

# === A) Disk I/O top consumers (during 60s) ===
Write-Host ""
Write-Host "=== A) Top CPU+RAM+IO consumers (snapshot avg) ==="
$samples = 6
$accum = @{}
for ($i = 0; $i -lt $samples; $i++) {
    Get-Process | ForEach-Object {
        $key = "$($_.Id):$($_.ProcessName)"
        if (-not $accum.ContainsKey($key)) {
            $accum[$key] = @{
                Name = $_.ProcessName
                Id = $_.Id
                CPUSamples = @()
                RAMSamples = @()
                IOReadSamples = @()
                IOWriteSamples = @()
            }
        }
        try {
            $accum[$key].CPUSamples += $_.CPU
            $accum[$key].RAMSamples += $_.WorkingSet64
            $accum[$key].IOReadSamples += $_.IO_ReadOperationCount + $_.IO_OtherOperationCount
            $accum[$key].IOWriteSamples += $_.IO_WriteOperationCount
        } catch {}
    }
    Start-Sleep -Seconds 5
}

# CPU delta + IO delta
Write-Host ""
Write-Host "TOP-10 CPU consumers (delta, 30s):"
$accum.Values | Where-Object { $_.CPUSamples.Count -ge 2 } | ForEach-Object {
    $first = $_.CPUSamples | Select-Object -First 1
    $last = $_.CPUSamples | Select-Object -Last 1
    if ($first -and $last) {
        $delta = $last - $first
    } else { $delta = 0 }
    [PSCustomObject]@{
        Name = $_.Name
        Id = $_.Id
        CPU_Delta_s = [math]::Round($delta, 2)
        RAM_MB = [math]::Round(($_.RAMSamples | Select-Object -Last 1) / 1MB, 1)
    }
} | Where-Object { $_.CPU_Delta_s -gt 0 } | Sort-Object CPU_Delta_s -Descending | Select-Object -First 10 | Format-Table -AutoSize

Write-Host "TOP-10 RAM consumers:"
$accum.Values | ForEach-Object {
    [PSCustomObject]@{
        Name = $_.Name
        Id = $_.Id
        RAM_MB = [math]::Round(($_.RAMSamples | Select-Object -Last 1) / 1MB, 1)
    }
} | Sort-Object RAM_MB -Descending | Select-Object -First 10 | Format-Table -AutoSize

# === B) Disk activity (top by IO ops) ===
Write-Host ""
Write-Host "=== B) Disk IO heavy hitters (delta IO_Operations) ==="
$accum.Values | Where-Object { $_.IOReadSamples.Count -ge 2 } | ForEach-Object {
    $rDelta = ($_.IOReadSamples | Select-Object -Last 1) - ($_.IOReadSamples | Select-Object -First 1)
    $wDelta = ($_.IOWriteSamples | Select-Object -Last 1) - ($_.IOWriteSamples | Select-Object -First 1)
    if ($rDelta + $wDelta -gt 0) {
        [PSCustomObject]@{
            Name = $_.Name
            Id = $_.Id
            IO_Read = $rDelta
            IO_Write = $wDelta
            IO_Total = $rDelta + $wDelta
        }
    }
} | Sort-Object IO_Total -Descending | Select-Object -First 10 | Format-Table -AutoSize

# === C) Foreground window changes (input-steal source) ===
Write-Host ""
Write-Host "=== C) Foreground window activity (input-steal trace) ==="
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class FgTracker {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);
    [DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr hWnd, out int processId);
}
"@
$fgChanges = @{}
$prevHwnd = [IntPtr]::Zero
$end = (Get-Date).AddSeconds(20)
while ((Get-Date) -lt $end) {
    $hwnd = [FgTracker]::GetForegroundWindow()
    if ($hwnd -ne $prevHwnd -and $hwnd -ne [IntPtr]::Zero) {
        $sb = New-Object System.Text.StringBuilder 256
        [FgTracker]::GetWindowText($hwnd, $sb, 256) | Out-Null
        $pid = 0
        [FgTracker]::GetWindowThreadProcessId($hwnd, [ref]$pid) | Out-Null
        $proc = (Get-Process -Id $pid -ErrorAction SilentlyContinue).ProcessName
        $title = $sb.ToString()
        $key = "$proc | $title"
        if ($key.Length -gt 100) { $key = $key.Substring(0,100) }
        if (-not $fgChanges.ContainsKey($key)) { $fgChanges[$key] = 0 }
        $fgChanges[$key]++
        $prevHwnd = $hwnd
    }
    Start-Sleep -Milliseconds 100
}
Write-Host "Foreground window changes (20s, 100ms poll):"
Write-Host "Total changes: $(($fgChanges.Values | Measure-Object -Sum).Sum)"
$fgChanges.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 15 | ForEach-Object {
    Write-Host ("  {0,3}x  {1}" -f $_.Value, $_.Key)
}

# === D) System counters ===
Write-Host ""
Write-Host "=== D) System performance ==="
$cpu = (Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 3).CounterSamples
$diskTime = (Get-Counter '\PhysicalDisk(_Total)\% Disk Time' -SampleInterval 1 -MaxSamples 3).CounterSamples
Write-Host "CPU avg %: $([math]::Round(($cpu | Measure-Object CookedValue -Average).Average, 1))"
Write-Host "Disk %: $([math]::Round(($diskTime | Measure-Object CookedValue -Average).Average, 1))"

$os = Get-CimInstance Win32_OperatingSystem
$used = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB, 1)
$total = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
Write-Host "RAM: $used GB / $total GB ($([math]::Round($used/$total*100, 1))%)"
