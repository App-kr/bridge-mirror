$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Currently visible powershell windows + their parent ==="
$visible = @()
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class W {
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr h, out int pid);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int n);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, System.Text.StringBuilder s, int n);
    public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc cb, IntPtr l);
}
"@
$results = New-Object System.Collections.ArrayList
$cb = [W+EnumWindowsProc] {
    param($h, $l)
    if (-not [W]::IsWindowVisible($h)) { return $true }
    $cn = New-Object System.Text.StringBuilder 256
    [W]::GetClassName($h, $cn, 256) | Out-Null
    if ($cn.ToString() -ne 'ConsoleWindowClass') { return $true }
    $pid = 0
    [W]::GetWindowThreadProcessId($h, [ref]$pid) | Out-Null
    $tn = New-Object System.Text.StringBuilder 256
    [W]::GetWindowText($h, $tn, 256) | Out-Null
    [void]$results.Add(@{ hwnd = $h; pid = $pid; title = $tn.ToString() })
    return $true
}
[W]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null

Write-Host ("Found {0} visible console windows" -f $results.Count)
foreach ($r in $results) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($r.pid)" -ErrorAction SilentlyContinue
    $pname = if ($proc) { $proc.Name } else { 'GONE' }
    $parent = if ($proc) { Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ParentProcessId)" -ErrorAction SilentlyContinue } else { $null }
    $parentName = if ($parent) { $parent.Name } else { 'GONE' }
    Write-Host ("  hwnd=0x{0:X}  pid={1}({2})  parent={3}  title={4}" -f $r.hwnd.ToInt64(), $r.pid, $pname, $parentName, $r.title.Substring(0,[Math]::Min(50,$r.title.Length)))
}

Write-Host ""
Write-Host "=== Background powershell from Antigravity (should NOT be hidden) ==="
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | ForEach-Object {
    $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.ParentProcessId)" -ErrorAction SilentlyContinue
    if ($parent -and $parent.Name -like 'Antigravity*') {
        Write-Host ("  pid={0}  visible={1}  cmd={2}" -f $_.ProcessId, '?', $_.CommandLine.Substring(0,[Math]::Min(80,$_.CommandLine.Length)))
    }
}
