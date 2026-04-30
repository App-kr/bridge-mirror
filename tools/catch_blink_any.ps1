$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class WW {
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr h, out int pid);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int n);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, System.Text.StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int L, T, R, B; }
}
"@

# Baseline (현재 visible)
$baseline = New-Object System.Collections.Generic.HashSet[Int64]
$cb1 = [WW+EnumProc] { param($h, $l) if ([WW]::IsWindowVisible($h)) { [void]$baseline.Add($h.ToInt64()) } ; return $true }
[WW]::EnumWindows($cb1, [IntPtr]::Zero) | Out-Null
Write-Host ("Baseline visible: {0}" -f $baseline.Count)
Write-Host "=== 25s ultra-fast (10ms) trace - ALL classes ==="
Write-Host ""

$detected = @{}
$end = (Get-Date).AddSeconds(25)
while ((Get-Date) -lt $end) {
    $cb2 = [WW+EnumProc] {
        param($h, $l)
        if ([WW]::IsWindowVisible($h)) {
            $hi = $h.ToInt64()
            if (-not $script:baseline.Contains($hi) -and -not $script:detected.ContainsKey($hi)) {
                $cn = New-Object System.Text.StringBuilder 128
                [WW]::GetClassName($h, $cn, 128) | Out-Null
                $tn = New-Object System.Text.StringBuilder 256
                [WW]::GetWindowText($h, $tn, 256) | Out-Null
                $pid = 0
                [WW]::GetWindowThreadProcessId($h, [ref]$pid) | Out-Null
                $rect = New-Object WW+RECT
                [WW]::GetWindowRect($h, [ref]$rect) | Out-Null
                $script:detected[$hi] = @{
                    cls = $cn.ToString()
                    title = $tn.ToString()
                    pid = $pid
                    ts = Get-Date
                    rect = "$($rect.L),$($rect.T) -> $($rect.R),$($rect.B)"
                }
            }
        }
        return $true
    }
    [WW]::EnumWindows($cb2, [IntPtr]::Zero) | Out-Null
    Start-Sleep -Milliseconds 10
}

Write-Host ("`nFound {0} new visible windows in 25s`n" -f $detected.Count)

foreach ($entry in $detected.Values | Sort-Object ts) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($entry.pid)" -ErrorAction SilentlyContinue
    $pname = if ($proc) { $proc.Name } else { 'GONE' }
    $parent = if ($proc) { Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ParentProcessId)" -ErrorAction SilentlyContinue } else { $null }
    $parentName = if ($parent) { $parent.Name } else { 'GONE' }
    Write-Host ("[{0:HH:mm:ss.fff}] cls={1,-25} pid={2}({3}) parent={4}" -f
        $entry.ts, $entry.cls, $entry.pid, $pname, $parentName)
    Write-Host ("    title={0}" -f $entry.title.Substring(0,[Math]::Min(70,$entry.title.Length)))
    Write-Host ("    rect={0}" -f $entry.rect)
}
