$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Real-time blink trace - 30s ==="
Write-Host "Watching for ALL new visible windows + their parent ancestry"
Write-Host ""

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class W2 {
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr h, out int pid);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int n);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, System.Text.StringBuilder s, int n);
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
}
"@

# 초기 hwnd 스냅샷
$snapHwnds = New-Object System.Collections.Generic.HashSet[Int64]
$cb = [W2+EnumProc] {
    param($h, $l)
    if ([W2]::IsWindowVisible($h)) { [void]$snapHwnds.Add($h.ToInt64()) }
    return $true
}
[W2]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null

$newHwnds = @{}
$end = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $end) {
    $cb2 = [W2+EnumProc] {
        param($h, $l)
        if ([W2]::IsWindowVisible($h) -and -not $snapHwnds.Contains($h.ToInt64())) {
            [void]$snapHwnds.Add($h.ToInt64())
            $cn = New-Object System.Text.StringBuilder 128
            [W2]::GetClassName($h, $cn, 128) | Out-Null
            $tn = New-Object System.Text.StringBuilder 256
            [W2]::GetWindowText($h, $tn, 256) | Out-Null
            $pid = 0
            [W2]::GetWindowThreadProcessId($h, [ref]$pid) | Out-Null
            $script:newHwnds[$h.ToInt64()] = @{ cls = $cn.ToString(); title = $tn.ToString(); pid = $pid; ts = Get-Date }
        }
        return $true
    }
    [W2]::EnumWindows($cb2, [IntPtr]::Zero) | Out-Null
    Start-Sleep -Milliseconds 50
}

Write-Host ("Found {0} NEW visible windows in 30s`n" -f $newHwnds.Count)

foreach ($entry in $newHwnds.Values | Sort-Object ts) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($entry.pid)" -ErrorAction SilentlyContinue
    $pname = if ($proc) { $proc.Name } else { 'GONE' }
    $parent = if ($proc) { Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ParentProcessId)" -ErrorAction SilentlyContinue } else { $null }
    $parentName = if ($parent) { $parent.Name } else { 'GONE' }
    Write-Host ("[{0:HH:mm:ss.fff}] cls={1}  pid={2}({3}) parent={4}  title={5}" -f
        $entry.ts, $entry.cls, $entry.pid, $pname, $parentName,
        $entry.title.Substring(0,[Math]::Min(60,$entry.title.Length)))
}
