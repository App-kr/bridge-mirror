$BASE = "Q:\Claudework\bridge base"
$AUTO = "$BASE\.backups\auto"

Write-Host "=== .backups\auto\ folder count after prune ==="
$folders = Get-ChildItem $AUTO -Directory -ErrorAction SilentlyContinue
foreach ($f in $folders) {
    $files = Get-ChildItem $f.FullName -File -ErrorAction SilentlyContinue
    Write-Host ("  " + $f.Name + " : " + $files.Count + " files")
}

$allDb = Get-ChildItem $AUTO -Recurse -Filter "*.db" -ErrorAction SilentlyContinue
$totalMB = [math]::Round(($allDb | Measure-Object Length -Sum).Sum / 1MB, 1)
Write-Host ("`nTotal .db files: " + $allDb.Count + " | Size: " + $totalMB + " MB")

Write-Host "`n=== last 5 log lines ==="
Get-Content "$BASE\.logs\auto_backup.log" -Tail 5 -ErrorAction SilentlyContinue
