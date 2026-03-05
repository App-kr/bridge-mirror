[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Import-Module AudioDeviceCmdlets
Write-Host "=== All Devices ==="
Get-AudioDevice -List | Select-Object Index, Default, Type, Name | Format-Table -AutoSize

# Also check PnP
Write-Host "=== PnP Captain ==="
Get-PnpDevice -Status OK | Where-Object { $_.FriendlyName -like "*Captain*" } | Select-Object Status, Class, FriendlyName | Format-Table -AutoSize
