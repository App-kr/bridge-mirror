# Ransomware check simplified
$cutoff = (Get-Date).AddHours(-24)

Write-Host "=== Files modified in Q:\ last 24h (non-git) ==="
try {
    $recent = Get-ChildItem "Q:\" -Recurse -Depth 3 -ErrorAction SilentlyContinue -Force |
        Where-Object { -not $_.PSIsContainer -and $_.LastWriteTime -gt $cutoff -and $_.FullName -notmatch "\\.git\\" }
    $recent | Sort-Object LastWriteTime -Descending | Select-Object -First 30 FullName, Length, LastWriteTime | Format-Table -AutoSize
    Write-Host "Total recent files: $($recent.Count)"
} catch {
    Write-Host "Error: $_"
}

Write-Host ""
Write-Host "=== Prefetch files (6-8 AM today) ==="
try {
    Get-ChildItem "C:\Windows\Prefetch" -Filter "*.pf" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime.Date -eq (Get-Date).Date -and $_.LastWriteTime.Hour -ge 6 -and $_.LastWriteTime.Hour -le 8 } |
        Sort-Object LastWriteTime |
        Select-Object Name, LastWriteTime | Format-Table -AutoSize
} catch {
    Write-Host "Prefetch error: $_"
}

Write-Host ""
Write-Host "=== Ransom note check ==="
try {
    Get-ChildItem "Q:\" -Recurse -Depth 2 -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match "READ|DECRYPT|RANSOM|HOW_TO|restore" } |
        Select-Object FullName, LastWriteTime | Format-Table -AutoSize
} catch {
    Write-Host "Ransom note check error: $_"
}
