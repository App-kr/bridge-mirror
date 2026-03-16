Write-Host "=== /health ==="
$h = Invoke-WebRequest -Uri "https://bridge-n7hk.onrender.com/health" -UseBasicParsing
Write-Host $h.Content

Write-Host "`n=== HTTP Headers ==="
$h.Headers.GetEnumerator() | ForEach-Object { Write-Host ("{0}: {1}" -f $_.Key, $_.Value) }
