$ErrorActionPreference = 'SilentlyContinue'

Write-Host "=== A) Any .hwp / .hwpx in Startup folders ==="
@("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup",
  "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup") | ForEach-Object {
    Get-ChildItem $_ -Recurse -Force -Include *.hwp,*.hwpx,*.lnk,*.vbs,*.bat,*.cmd,*.ps1 -ErrorAction SilentlyContinue |
        Select FullName, Length, LastWriteTime | Format-Table -AutoSize
}

Write-Host "`n=== B) Registry autorun (HKCU + HKLM, Run/RunOnce/RunServices) ==="
$keys = @(
  'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run',
  'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce',
  'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run',
  'HKLM:\Software\Microsoft\Windows\CurrentVersion\RunOnce',
  'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run',
  'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\RunOnce'
)
foreach ($k in $keys) {
    Write-Host "--- $k ---"
    $v = Get-ItemProperty $k -ErrorAction SilentlyContinue
    if ($v) { $v.PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' } | ForEach-Object { Write-Host ("  {0} = {1}" -f $_.Name,$_.Value) } }
}

Write-Host "`n=== C) Hancom/HWP related autoruns ==="
Get-ChildItem "HKCU:\Software" -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'Hnc|Hancom|Hwp' } | Select-Object Name | Format-Table -AutoSize | Out-String | Write-Host

Write-Host "`n=== D) Recent document history (HWP recently opened) ==="
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs\.hwp" -ErrorAction SilentlyContinue | Out-String | Write-Host

Write-Host "`n=== E) Scripts referencing hwp / hancom anywhere ==="
$rootsSearch = @("Q:\Claudework","C:\Users\Scarlett\.claude","C:\Users\Scarlett\AppData\Local","C:\Users\Scarlett\AppData\Roaming")
foreach ($r in $rootsSearch) {
    if (Test-Path $r) {
        Get-ChildItem $r -Recurse -Include *.ps1,*.vbs,*.bat,*.cmd,*.py -ErrorAction SilentlyContinue -Force |
            Select-String -Pattern 'hwp|hancom|hncapp|Hwp.exe|HncApp' -SimpleMatch -ErrorAction SilentlyContinue |
            Select-Object Path, LineNumber, Line | Format-Table -AutoSize -Wrap
    }
}

Write-Host "`n=== F) Task Scheduler last-run history (last 30) ==="
Get-ScheduledTask | Where-Object { $_.TaskPath -notlike '\Microsoft\*' } | ForEach-Object {
    $i = $_ | Get-ScheduledTaskInfo
    [PSCustomObject]@{
        Name     = ($_.TaskPath + $_.TaskName)
        LastRun  = $i.LastRunTime
        NextRun  = $i.NextRunTime
        Result   = $i.LastTaskResult
    }
} | Sort-Object LastRun -Descending | Select-Object -First 30 | Format-Table -AutoSize
