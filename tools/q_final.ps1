$ErrorActionPreference = "SilentlyContinue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Final Q Drive Cleanup ==="

# Folder name decoding:
# Hex AC C0 C4 C9 F5 AC 20 C7 -> UTF-16LE -> so jin gong yu (sojin_shared)
# Files: "sojin_school (N).png" x36

# STEP 1: Rename the remaining garbled folder
Write-Host "`n[1] Renaming garbled folder..."
$garbled = Get-ChildItem "Q:\" -Force -Directory | Where-Object {
    ($_.Name -replace '[^\x20-\x7E]', '').Length -ne $_.Name.Length
}
foreach ($d in $garbled) {
    $files = Get-ChildItem $d.FullName -Force -File -ErrorAction SilentlyContinue
    $exts = ($files | ForEach-Object { $_.Extension.ToLower() } | Sort-Object -Unique) -join ","
    $cnt = $files.Count
    Write-Host "  Found: [$($d.Name)] - $cnt files, ext: $exts"

    # 36 PNG files - school images (sojin_school pattern)
    if ($exts -match "\.png" -and $cnt -ge 30) {
        $newName = "images_sojin_school"
        $newPath = "Q:\$newName"
        if (-not (Test-Path $newPath)) {
            Rename-Item $d.FullName $newName -Force
            Write-Host "  RENAMED -> $newName"
        } else {
            Write-Host "  TARGET EXISTS: $newName"
        }
    } else {
        Write-Host "  UNIDENTIFIED - skipping"
    }
}

# STEP 2: Archive Filezilla (only has log file, FTP server artifact)
Write-Host "`n[2] Archiving Filezilla..."
$arch = "Q:\_archive"
if (-not (Test-Path $arch)) {
    New-Item -Path $arch -ItemType Directory | Out-Null
}
$fz = "Q:\Filezilla"
if (Test-Path $fz) {
    $fc = (Get-ChildItem $fz -Force -Recurse -File -ErrorAction SilentlyContinue).Count
    Write-Host "  Filezilla has $fc file(s) - archiving as FTP log artifact"
    Move-Item $fz $arch -Force
    Write-Host "  ARCHIVED: Filezilla -> _archive"
}

# STEP 3: Final structure
Write-Host "`n=== FINAL Q:\ ==="
Get-ChildItem "Q:\" -Force | Where-Object {
    $_.Name -ne "`$Recycle.Bin" -and $_.Name -notmatch "System Volume"
} | Sort-Object Name | ForEach-Object {
    $tag = if ($_.PSIsContainer) { "[D]" } else { "[F]" }
    Write-Host "  $tag $($_.Name)"
}
Write-Host "`nDone."
