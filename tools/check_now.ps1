# 즉시 연결 상태 확인
$cutoff = (Get-Date).AddMinutes(-5)

Write-Host "=== PnP Device Status ===" -ForegroundColor Cyan
Get-PnpDevice | Where-Object { $_.FriendlyName -match "N460|ABKO" } |
    Select-Object Status, FriendlyName | Format-Table -AutoSize

Write-Host "=== Recent Kernel-PnP events (last 5min) ===" -ForegroundColor Cyan
$events = Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -MaxEvents 200 |
          Where-Object { $_.TimeCreated -gt $cutoff }
Write-Host "Events in last 5min: $($events.Count)"
$events | Group-Object Id | Sort-Object Count -Descending |
    Select-Object Name, Count | Format-Table -AutoSize

Write-Host "=== Recent USB connection events ===" -ForegroundColor Cyan
$events | Where-Object { $_.Id -eq 400 -or $_.Id -eq 410 } |
    Select-Object TimeCreated, Id, Message | Format-List

Write-Host "=== Audio device list ===" -ForegroundColor Cyan
Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue
Get-AudioDevice -List | Select-Object Default, Type, Name | Format-Table -AutoSize
