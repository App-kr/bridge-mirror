# Check prefetch files around the time of HND folder creation (6:10 AM)
$pf = Get-ChildItem "C:\Windows\Prefetch" -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime.Date -eq (Get-Date).Date } |
    Sort-Object LastWriteTime

Write-Host "=== All prefetch files run TODAY (sorted by time) ==="
$pf | Select-Object Name, LastWriteTime | Format-Table -AutoSize

Write-Host ""
Write-Host "=== py313 output files ==="
Get-Content "C:\Temp\py313_out.txt" -ErrorAction SilentlyContinue
Write-Host "(py313_out.txt above)"
Get-Content "C:\Temp\py313_err.txt" -ErrorAction SilentlyContinue
Write-Host "(py313_err.txt above)"

Write-Host ""
Write-Host "=== junctions_done.txt content ==="
Get-Content "C:\Temp\junctions_done.txt" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== What Python scripts might create C:\Temp files ==="
Select-String -Path "Q:\Claudework\bridge base\tools\render_monitor.py" -Pattern "C:\\Temp|py313" -ErrorAction SilentlyContinue |
    Select-Object LineNumber, Line | Format-Table -AutoSize

Write-Host ""
Write-Host "=== Check reg_task.ps1 in C:\Temp (March 13 task) ==="
Get-Content "C:\Temp\reg_task.ps1" -ErrorAction SilentlyContinue
