# D: 드라이브 상위 폴더 용량 분석
Write-Host "=== D: 드라이브 폴더별 용량 ==="
Get-ChildItem "D:\" -Directory | ForEach-Object {
    $size = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    $sizeGB = [math]::Round($size/1GB, 2)
    $name = $_.Name
    Write-Host "${sizeGB}GB  $name"
} | Sort-Object

Write-Host ""
Write-Host "=== D: 내 임시/정크 파일 ==="
$patterns = @("*.tmp", "*.log", "*.dmp", "*.bak")
foreach ($p in $patterns) {
    $files = Get-ChildItem "D:\" -Recurse -Filter $p -File -ErrorAction SilentlyContinue
    if ($files) {
        $totalMB = [math]::Round(($files | Measure-Object -Property Length -Sum).Sum/1MB, 1)
        Write-Host "$p : $($files.Count)개  ${totalMB}MB"
    }
}
