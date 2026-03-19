# Find Adobe processes and scheduled tasks
Write-Host "=== Running Adobe Processes ==="
Get-Process | Where-Object { $_.Name -like '*Adobe*' -or $_.Name -like '*Acrobat*' } | Select-Object Name, Id, Path | Format-Table -AutoSize

Write-Host "=== Adobe Scheduled Tasks ==="
Get-ScheduledTask | Where-Object { $_.TaskName -like '*Adobe*' -or $_.TaskName -like '*Acrobat*' } | Select-Object TaskName, State | Format-Table -AutoSize

Write-Host "=== Adobe Services ==="
Get-Service | Where-Object { $_.Name -like '*Adobe*' -or $_.DisplayName -like '*Adobe*' } | Select-Object Name, Status, StartType | Format-Table -AutoSize
