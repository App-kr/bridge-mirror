$r = Invoke-WebRequest -Uri "https://bridge-n7hk.onrender.com/openapi.json" -UseBasicParsing
$content = $r.Content
$m = [regex]::Matches($content, '"maxLength"\s*:\s*(\d+)')
foreach ($match in $m) {
    Write-Host ("maxLength: " + $match.Groups[1].Value)
}
Write-Host ("HTTP Status: " + $r.StatusCode)
