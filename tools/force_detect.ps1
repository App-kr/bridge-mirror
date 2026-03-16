# Force device scan and check N460
Write-Host "Scanning devices..." -ForegroundColor Cyan
pnputil /scan-devices 2>$null
Start-Sleep -Seconds 3

Write-Host "=== N460 Status After Scan ===" -ForegroundColor Cyan
Get-PnpDevice | Where-Object FriendlyName -match "N460|ABKO" |
    Select-Object Status, FriendlyName, InstanceId | Format-List

Write-Host "=== All USB devices with OK status ===" -ForegroundColor Cyan
Get-PnpDevice -Class USB | Where-Object Status -eq OK |
    Select-Object Status, FriendlyName | Format-Table -AutoSize

Write-Host "=== Audio devices ===" -ForegroundColor Cyan
Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue
Get-AudioDevice -List | Select-Object Default, Type, Name | Format-Table -AutoSize

Write-Host "=== Recent PnP events (last 2min) ===" -ForegroundColor Cyan
$cutoff = (Get-Date).AddMinutes(-2)
$ev = Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -MaxEvents 100 |
      Where-Object { $_.TimeCreated -gt $cutoff }
Write-Host "Events: $($ev.Count)"
if ($ev.Count -gt 0) {
    $ev | Select-Object TimeCreated, Id | Format-Table -AutoSize
}
