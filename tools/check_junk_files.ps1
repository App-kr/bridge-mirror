# 문제 파일 점검
$BASE = "Q:\Claudework\bridge base"

Write-Host "=== master.db 백업 파일들 ==="
Get-ChildItem "$BASE\master.db*" |
    Select-Object Name, @{N='SizeMB';E={[math]::Round($_.Length/1MB,1)}}, LastWriteTime |
    Format-Table -AutoSize

Write-Host "=== 이상 파일 점검 ==="
$junkFiles = @("nul", "null", "=1.34.0", "_parent_pid.txt",
               "overlay_stop.flag", "overlay_state.json",
               "temp_bridge_logo.jpg", "tmp_jobs.json", "tmp_stats.json", "tmp_visa.json")
foreach ($f in $junkFiles) {
    $fp = "$BASE\$f"
    if (Test-Path $fp) {
        $item = Get-Item $fp
        $size = $item.Length
        $age  = (Get-Date) - $item.LastWriteTime
        Write-Host "$f | ${size}bytes | 수정: $($item.LastWriteTime.ToString('MM-dd HH:mm')) | ${[int]$age.TotalDays}일 전"
    }
}

Write-Host ""
Write-Host "=== CLAUDE.md 백업본 ==="
Get-ChildItem "$BASE\CLAUDE.md*" |
    Select-Object Name, @{N='SizeMB';E={[math]::Round($_.Length/1MB,2)}}, LastWriteTime |
    Format-Table -AutoSize
