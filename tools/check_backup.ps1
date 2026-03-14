$path = "Q:\Claudework\_BACKUP"

Write-Host "=== _BACKUP 하위 폴더별 크기 ==="
Get-ChildItem -Path $path -Directory -ErrorAction SilentlyContinue |
    ForEach-Object {
        $size = (Get-ChildItem $_.FullName -Recurse -ErrorAction SilentlyContinue |
            Measure-Object -Property Length -Sum).Sum
        [PSCustomObject]@{
            Folder = $_.Name
            SizeGB = [math]::Round($size/1GB, 2)
            SizeMB = [math]::Round($size/1MB, 0)
            FileCount = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue).Count
        }
    } | Sort-Object SizeGB -Descending | Format-Table -AutoSize

Write-Host ""
Write-Host "=== _BACKUP 직접 파일 목록 ==="
Get-ChildItem -Path $path -File -ErrorAction SilentlyContinue |
    Select-Object Name, @{N='SizeMB';E={[math]::Round($_.Length/1MB,1)}}, LastWriteTime |
    Sort-Object SizeMB -Descending | Select-Object -First 20 | Format-Table -AutoSize
