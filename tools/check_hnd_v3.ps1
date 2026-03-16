# Simple HND check - just text and metadata
$items = Get-ChildItem "Q:\" -ErrorAction SilentlyContinue
$hnd = $items | Where-Object { $_.Name -like "*HND*" }
$folder = $hnd.FullName
$jpgPath = Join-Path $folder "'hnD'H%.jpg"

Write-Host "JPG path: $jpgPath"
Write-Host "Exists: $(Test-Path $jpgPath)"

$bytes = [System.IO.File]::ReadAllBytes($jpgPath)
Write-Host "Size: $($bytes.Length)"

# Extract readable ASCII strings longer than 4 chars
$sb = New-Object System.Text.StringBuilder
$run = 0
$starts = @()
for ($i = 0; $i -lt [Math]::Min($bytes.Length, 5000); $i++) {
    $b = $bytes[$i]
    if ($b -ge 0x20 -and $b -le 0x7E) {
        $sb.Append([char]$b) | Out-Null
        $run++
    } else {
        if ($run -ge 5) {
            $s = $sb.ToString()
            if ($s -match '[a-zA-Z]{3}') {
                $starts += $s
            }
        }
        $sb.Clear() | Out-Null
        $run = 0
    }
}
Write-Host ""
Write-Host "=== Embedded strings (>4 chars) in JPEG header ==="
$starts | Format-List
