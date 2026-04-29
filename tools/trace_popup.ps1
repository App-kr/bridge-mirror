$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Tracking ALL visible windows (any class) - 25s, 30ms poll ==="

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class WAll {
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr h, out int pid);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int n);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, System.Text.StringBuilder s, int n);
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
}
"@

# 초기 baseline (현재 visible 모두)
$baseline = New-Object System.Collections.Generic.HashSet[Int64]
$cb1 = [WAll+EnumProc] {
    param($h, $l)
    if ([WAll]::IsWindowVisible($h)) { [void]$baseline.Add($h.ToInt64()) }
    return $true
}
[WAll]::EnumWindows($cb1, [IntPtr]::Zero) | Out-Null
Write-Host ("Baseline: {0} visible windows`n" -f $baseline.Count)

$detected = @{}
$end = (Get-Date).AddSeconds(25)
while ((Get-Date) -lt $end) {
    $cb2 = [WAll+EnumProc] {
        param($h, $l)
        if ([WAll]::IsWindowVisible($h)) {
            $hi = $h.ToInt64()
            if (-not $script:baseline.Contains($hi) -and -not $script:detected.ContainsKey($hi)) {
                $cn = New-Object System.Text.StringBuilder 128
                [WAll]::GetClassName($h, $cn, 128) | Out-Null
                $tn = New-Object System.Text.StringBuilder 256
                [WAll]::GetWindowText($h, $tn, 256) | Out-Null
                $pid = 0
                [WAll]::GetWindowThreadProcessId($h, [ref]$pid) | Out-Null
                $script:detected[$hi] = @{
                    cls = $cn.ToString()
                    title = $tn.ToString()
                    pid = $pid
                    ts = Get-Date
                }
            }
        }
        return $true
    }
    [WAll]::EnumWindows($cb2, [IntPtr]::Zero) | Out-Null
    Start-Sleep -Milliseconds 30
}

Write-Host ("Found {0} new visible windows in 25s`n" -f $detected.Count)

foreach ($entry in $detected.Values | Sort-Object ts) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($entry.pid)" -ErrorAction SilentlyContinue
    $pname = if ($proc) { $proc.Name } else { 'GONE' }
    $parent = if ($proc) { Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ParentProcessId)" -ErrorAction SilentlyContinue } else { $null }
    $parentName = if ($parent) { $parent.Name } else { 'GONE' }
    Write-Host ("[{0:HH:mm:ss.fff}] cls={1,-25} pid={2}({3}) parent={4}  title={5}" -f
        $entry.ts, $entry.cls, $entry.pid, $pname, $parentName,
        $entry.title.Substring(0,[Math]::Min(60,$entry.title.Length)))
}
