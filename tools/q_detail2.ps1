$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== Antigravity ==="
Get-ChildItem "Q:\Antigravity" -Force | Select-Object Mode, Name, LastWriteTime | Format-Table -AutoSize

Write-Host "=== Code ==="
Get-ChildItem "Q:\Code" -Force | Select-Object Mode, Name, LastWriteTime | Format-Table -AutoSize

Write-Host "=== Codex testing ==="
Get-ChildItem "Q:\Codex testing" -Force | Select-Object Mode, Name, LastWriteTime | Format-Table -AutoSize

Write-Host "=== Bridge web_old top ==="
Get-ChildItem "Q:\Bridge web_old" -Force | Select-Object Mode, Name, LastWriteTime | Format-Table -AutoSize

Write-Host "=== data folder ==="
Get-ChildItem "Q:\data" -Force -Recurse | Select-Object FullName, Length | Format-Table -AutoSize

Write-Host "=== Acrobat Pro ==="
Get-ChildItem "Q:\Acrobat Pro" -Force | Select-Object Mode, Name | Format-Table -AutoSize

Write-Host "=== _SECURITY_QUARANTINE ==="
Get-ChildItem "Q:\_SECURITY_QUARANTINE" -Force | Select-Object Mode, Name | Format-Table -AutoSize

Write-Host "=== 'HND'H% full name check ==="
$item = Get-Item "Q:\'HND'H%" -Force -ErrorAction SilentlyContinue
if (-not $item) {
    $item = Get-ChildItem "Q:\" -Force | Where-Object { $_.Name -like "*HND*" -or $_.Name -like "*hnD*" }
}
if ($item) { Write-Host "Full name: [$($item.Name)]" }
