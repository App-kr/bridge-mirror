# Check file headers of 'HND'H% files to determine if encrypted
$items = Get-ChildItem "Q:\" -ErrorAction SilentlyContinue
$hnd = $items | Where-Object { $_.Name -like "*HND*" }
$folder = $hnd.FullName

Write-Host "Checking folder: $folder"

# Check the .jpg file header
$jpgPath = Join-Path $folder "'hnD'H%.jpg"
if (Test-Path $jpgPath) {
    $bytes = [System.IO.File]::ReadAllBytes($jpgPath)
    $header = ($bytes[0..15] | ForEach-Object { "{0:X2}" -f $_ }) -join " "
    Write-Host "JPG header (hex): $header"
    $size = $bytes.Length
    Write-Host "File size: $size bytes"

    # Check if JPEG magic bytes (FF D8 FF)
    if ($bytes[0] -eq 0xFF -and $bytes[1] -eq 0xD8 -and $bytes[2] -eq 0xFF) {
        Write-Host "JPG: Valid JPEG signature"
    } else {
        Write-Host "JPG: NOT a valid JPEG - possible encryption/corruption"
    }
}

# Check the .bmp file header
$bmpPath = Join-Path $folder "'hnD'H%.bmp"
if (Test-Path $bmpPath) {
    $bytes = [System.IO.File]::ReadAllBytes($bmpPath)
    $header = ($bytes[0..15] | ForEach-Object { "{0:X2}" -f $_ }) -join " "
    Write-Host "BMP header (hex): $header"
    if ($bytes[0] -eq 0x42 -and $bytes[1] -eq 0x4D) {
        Write-Host "BMP: Valid BMP signature (BM)"
    } else {
        Write-Host "BMP: NOT a valid BMP"
    }
}

# Check the .docx file header (should be PK ZIP)
$docxPath = Join-Path $folder "'hnD'H%.docx"
if (Test-Path $docxPath) {
    $bytes = [System.IO.File]::ReadAllBytes($docxPath)
    $header = ($bytes[0..15] | ForEach-Object { "{0:X2}" -f $_ }) -join " "
    Write-Host "DOCX header (hex): $header"
    if ($bytes[0] -eq 0x50 -and $bytes[1] -eq 0x4B) {
        Write-Host "DOCX: Valid ZIP/Office Open XML signature (PK)"
    } else {
        Write-Host "DOCX: NOT a valid DOCX/ZIP"
    }
}

# Compare first 32 bytes of all files to see if identical
Write-Host ""
Write-Host "=== Comparing first 32 bytes across all files ==="
$files = Get-ChildItem $folder
$firstBytes = @{}
foreach ($f in $files) {
    $b = [System.IO.File]::ReadAllBytes($f.FullName)
    $key = ($b[0..31] | ForEach-Object { "{0:X2}" -f $_ }) -join ""
    $firstBytes[$f.Name] = $key
    Write-Host "$($f.Name): $key"
}

# Check if all first bytes are identical
$unique = $firstBytes.Values | Select-Object -Unique
if ($unique.Count -eq 1) {
    Write-Host ""
    Write-Host "WARNING: ALL files have IDENTICAL first 32 bytes - ransomware indicator!"
} else {
    Write-Host ""
    Write-Host "Files have different headers - may be legitimate"
}
