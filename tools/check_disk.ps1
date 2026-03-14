$path = "Q:\Claudework"

Write-Host "=== Q:\Claudework 전체 용량 ==="
$total = Get-ChildItem -Path $path -Recurse -ErrorAction SilentlyContinue |
    Measure-Object -Property Length -Sum
Write-Host ("TotalGB: " + [math]::Round($total.Sum/1GB, 2))

Write-Host ""
Write-Host "=== 폴더별 크기 (상위 10) ==="
Get-ChildItem -Path $path -Directory |
    ForEach-Object {
        $size = (Get-ChildItem $_.FullName -Recurse -ErrorAction SilentlyContinue |
            Measure-Object -Property Length -Sum).Sum
        [PSCustomObject]@{
            Folder = $_.Name
            SizeGB = [math]::Round($size/1GB, 2)
            SizeMB = [math]::Round($size/1MB, 0)
        }
    } | Sort-Object SizeGB -Descending | Select-Object -First 10 | Format-Table -AutoSize
