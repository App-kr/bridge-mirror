# Investigate 'HND'H% folder origin
# Try to view the JPEG metadata
$items = Get-ChildItem "Q:\" -ErrorAction SilentlyContinue
$hnd = $items | Where-Object { $_.Name -like "*HND*" }
$folder = $hnd.FullName
$jpgPath = Join-Path $folder "'hnD'H%.jpg"

Write-Host "=== JPEG EXIF metadata ==="
try {
    $bytes = [System.IO.File]::ReadAllBytes($jpgPath)
    # Check for EXIF marker (FF E1)
    $offset = 2
    if ($bytes[offset] -eq 0xFF -and $bytes[$offset+1] -eq 0xE1) {
        # Skip APP1 marker + length
        $len = ($bytes[$offset+2] -shl 8) + $bytes[$offset+3]
        $exifStart = $offset + 4
        # EXIF header: 45 78 69 66 00 00
        $exifHeader = [System.Text.Encoding]::ASCII.GetString($bytes, $exifStart, 6)
        Write-Host "EXIF header: $exifHeader"
    }

    # Try to get image dimensions from JPEG SOF marker
    for ($i = 0; $i -lt [Math]::Min($bytes.Length-3, 10000); $i++) {
        if ($bytes[$i] -eq 0xFF -and ($bytes[$i+1] -ge 0xC0 -and $bytes[$i+1] -le 0xC3)) {
            $height = ($bytes[$i+5] -shl 8) + $bytes[$i+6]
            $width = ($bytes[$i+7] -shl 8) + $bytes[$i+8]
            Write-Host "Image dimensions: ${width}x${height}"
            break
        }
    }

    # Check if there's any text in first 2KB (might contain creator info)
    $start = [System.Text.Encoding]::ASCII.GetString($bytes, 0, [Math]::Min(2048, $bytes.Length))
    $readable = $start -replace '[^\x20-\x7E]', ' '
    Write-Host "Readable text in header:"
    Write-Host ($readable.Substring(0, [Math]::Min(500, $readable.Length)))
} catch {
    Write-Host "Error reading JPEG: $_"
}

Write-Host ""
Write-Host "=== nxTS log files ==="
if (Test-Path "C:\Temp\nxweb_debug.log") {
    Write-Host "nxweb_debug.log exists (from 2023)"
    Get-Content "C:\Temp\nxweb_debug.log" -ErrorAction SilentlyContinue | Select-Object -Last 10
}

# Check nxTS installation
Write-Host ""
Write-Host "=== nxTS files ==="
Get-ChildItem "C:\Program Files (x86)\nxTS" -ErrorAction SilentlyContinue | Select-Object Name, Length, LastWriteTime | Format-Table

# Check if nxTS has any config about honeypot/canary files
Get-ChildItem "C:\ProgramData" -Filter "*nxTS*" -Recurse -Depth 2 -ErrorAction SilentlyContinue | Select-Object Name, LastWriteTime | Format-Table

Write-Host ""
Write-Host "=== AhnLab Safe Transaction files ==="
if (Test-Path "C:\Program Files\AhnLab\Safe Transaction") {
    Get-ChildItem "C:\Program Files\AhnLab\Safe Transaction" -ErrorAction SilentlyContinue | Select-Object Name, Length | Format-Table
}
