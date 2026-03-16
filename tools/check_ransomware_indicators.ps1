# Check for ransomware indicators
Write-Host "=== 1. Files modified in Q:\ in last 24 hours ==="
$cutoff = (Get-Date).AddHours(-24)
Get-ChildItem "Q:\" -Recurse -Depth 2 -ErrorAction SilentlyContinue |
    Where-Object { -not $_.PSIsContainer -and $_.LastWriteTime -gt $cutoff } |
    Sort-Object LastWriteTime -Descending |
    Select-Object FullName, Length, LastWriteTime |
    Format-Table -AutoSize

Write-Host ""
Write-Host "=== 2. Prefetch: What ran around 6:00-7:00 AM today ==="
$pf = Get-ChildItem "C:\Windows\Prefetch" -Filter "*.pf" -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt (Get-Date "2026-03-14 06:00") -and $_.LastWriteTime -lt (Get-Date "2026-03-14 08:00") } |
    Sort-Object LastWriteTime
$pf | Select-Object Name, LastWriteTime | Format-Table -AutoSize

Write-Host ""
Write-Host "=== 3. Recent Security Event (Process Creation 4688) ==="
Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4688; StartTime=(Get-Date).AddHours(-12)} -MaxEvents 50 -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -like "*wscript*" -or $_.Message -like "*cscript*" } |
    Select-Object TimeCreated, @{N="Process";E={($_.Message -split "`n" | Where-Object {$_ -like "*New Process Name*"}) -replace ".*: ",""}} |
    Format-Table -AutoSize

Write-Host ""
Write-Host "=== 4. Check for ransom note files ==="
Get-ChildItem "Q:\" -Recurse -Depth 2 -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match "READ_ME|DECRYPT|RANSOM|HOW_TO|restore" -and -not $_.PSIsContainer } |
    Select-Object FullName, LastWriteTime | Format-Table -AutoSize
