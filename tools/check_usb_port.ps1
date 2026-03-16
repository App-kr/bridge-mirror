# USB 포트 및 컨트롤러 상태 점검
$cutoff = (Get-Date).AddMinutes(-10)
$events = Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -MaxEvents 500 |
          Where-Object { $_.TimeCreated -gt $cutoff }
Write-Host "Events in last 10min: $($events.Count)"
if ($events.Count -gt 0) {
    $events | Group-Object Id | Sort-Object Name | Select-Object Name, Count | Format-Table
}

Write-Host "=== USB Controller Status ===" -ForegroundColor Cyan
Get-PnpDevice -Class "USB" |
    Where-Object { $_.FriendlyName -match "Host|Controller|AMD|NVIDIA|Intel" } |
    Select-Object Status, FriendlyName | Format-Table -AutoSize

Write-Host "=== USB Root Hub Status ===" -ForegroundColor Cyan
Get-PnpDevice -Class "USB" |
    Where-Object { $_.FriendlyName -match "Root Hub" } |
    Select-Object Status, FriendlyName, InstanceId | Format-Table -AutoSize

Write-Host "=== USB Error Check ===" -ForegroundColor Cyan
Get-PnpDevice -Class "USB" | Where-Object { $_.Status -ne "OK" } |
    Select-Object Status, FriendlyName | Format-Table -AutoSize
