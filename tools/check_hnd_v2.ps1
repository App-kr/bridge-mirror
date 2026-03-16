# Simplified HND investigation
$items = Get-ChildItem "Q:\" -ErrorAction SilentlyContinue
$hnd = $items | Where-Object { $_.Name -like "*HND*" }
$folder = $hnd.FullName
$jpgPath = Join-Path $folder "'hnD'H%.jpg"

Write-Host "=== JPEG readable text in first 2KB ==="
$bytes = [System.IO.File]::ReadAllBytes($jpgPath)
$ascii = [System.Text.Encoding]::ASCII.GetString($bytes, 0, [Math]::Min(2048, $bytes.Length))
$clean = [System.Text.RegularExpressions.Regex]::Replace($ascii, '[^\x20-\x7E\r\n]', ' ')
Write-Host ($clean.Substring(0, [Math]::Min(800, $clean.Length)))

Write-Host ""
Write-Host "=== nxTS installation ==="
Get-ChildItem "C:\Program Files (x86)\nxTS" -ErrorAction SilentlyContinue | Select-Object Name, Length | Format-Table

Write-Host "=== AhnLab Safe Transaction ==="
Get-ChildItem "C:\Program Files\AhnLab\Safe Transaction" -ErrorAction SilentlyContinue | Select-Object Name | Format-Table

Write-Host "=== ProgramData RAONWIZ ==="
Get-ChildItem "C:\ProgramData\RAONWIZ" -Recurse -Depth 2 -ErrorAction SilentlyContinue | Select-Object FullName, Length, LastWriteTime | Format-Table

Write-Host "=== Check if any process has 'HND'H%' folder open ==="
handle "Q:\'HND'H%" 2>&1 -ErrorAction SilentlyContinue
