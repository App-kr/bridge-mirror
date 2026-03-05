[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Get-PnpDevice | Where-Object { $_.FriendlyName -like '*Captain*' -or $_.FriendlyName -like '*780*' } | Select-Object Status, Class, FriendlyName, InstanceId | Format-Table -AutoSize
