$ErrorActionPreference = "SilentlyContinue"
Write-Host "=== Q Drive Cleanup ==="

# STEP 1: Delete truly empty folders
Write-Host "`n[1] Deleting empty folders..."
$emptyTargets = @("Acrobat Pro", "_SECURITY_QUARANTINE")
foreach ($n in $emptyTargets) {
    $p = "Q:\$n"
    if (Test-Path $p) {
        $cnt = (Get-ChildItem $p -Force -Recurse -ErrorAction SilentlyContinue).Count
        if ($cnt -eq 0) {
            Remove-Item $p -Force -Recurse
            Write-Host "  DELETED (empty): $n"
        } else {
            Write-Host "  SKIP (has items): $n"
        }
    }
}

# Filezilla - only empty Logs folder
$fz = "Q:\Filezilla"
if (Test-Path $fz) {
    $fc = (Get-ChildItem $fz -Force -Recurse -File -ErrorAction SilentlyContinue).Count
    if ($fc -eq 0) {
        Remove-Item $fz -Force -Recurse
        Write-Host "  DELETED (empty): Filezilla"
    }
}

# STEP 2: Consolidate .backups into _BACKUPS
Write-Host "`n[2] Consolidating .backups..."
$src = "Q:\.backups"
$dst = "Q:\_BACKUPS"
if (Test-Path $src) {
    Get-ChildItem $src -Force | ForEach-Object {
        $dstItem = Join-Path $dst $_.Name
        if (-not (Test-Path $dstItem)) {
            Move-Item $_.FullName $dst -Force
            Write-Host "  MOVED: $($_.Name) to _BACKUPS"
        } else {
            Write-Host "  EXISTS in _BACKUPS: $($_.Name)"
        }
    }
    $rem = (Get-ChildItem $src -Force).Count
    if ($rem -eq 0) {
        Remove-Item $src -Force
        Write-Host "  DELETED empty: .backups"
    }
}

# STEP 3: Rename garbled folders by content
Write-Host "`n[3] Renaming garbled folders..."
$allDirs = Get-ChildItem "Q:\" -Force -Directory
foreach ($dir in $allDirs) {
    $nm = $dir.Name
    $isAscii = ($nm -replace '[^\x20-\x7E]', '').Length -eq $nm.Length
    if ($isAscii) { continue }

    $files = Get-ChildItem $dir.FullName -Force -File -ErrorAction SilentlyContinue
    $exts  = ($files | ForEach-Object { $_.Extension.ToLower() } | Sort-Object -Unique) -join ","
    $cnt   = $files.Count

    $newNm = $null
    if ($exts -match "\.png" -and $cnt -gt 10) {
        $newNm = "images_students"
    } elseif ($exts -match "\.jpg" -and $cnt -eq 1) {
        $newNm = "profile_builder_sample"
    }

    if ($newNm) {
        $newPath = "Q:\$newNm"
        if (-not (Test-Path $newPath)) {
            Rename-Item $dir.FullName $newNm -Force
            Write-Host "  RENAMED: garbled -> $newNm"
        } else {
            Write-Host "  TARGET EXISTS: $newNm"
        }
    } else {
        Write-Host "  UNIDENTIFIED: [$nm] ($cnt files, $exts)"
    }
}

# STEP 4: Rename 'HND'H% folder
Write-Host "`n[4] Handling HND folder..."
$hnd = Get-ChildItem "Q:\" -Force -Directory | Where-Object { $_.Name -match "HND|hnD|hnD" }
if ($hnd) {
    $newPath = "Q:\file_type_icons"
    if (-not (Test-Path $newPath)) {
        Rename-Item $hnd.FullName "file_type_icons" -Force
        Write-Host "  RENAMED: [$($hnd.Name)] -> file_type_icons"
    }
}

# STEP 5: Create _archive and move old items
Write-Host "`n[5] Archiving old items..."
$arch = "Q:\_archive"
if (-not (Test-Path $arch)) {
    New-Item -Path $arch -ItemType Directory | Out-Null
    Write-Host "  CREATED: _archive"
}

$toArchive = @("Codex testing", "_REPORTS")
foreach ($n in $toArchive) {
    $p = "Q:\$n"
    if (Test-Path $p) {
        Move-Item $p $arch -Force
        Write-Host "  ARCHIVED: $n"
    }
}

# STEP 6: Final structure
Write-Host "`n=== FINAL Q:\ ==="
Get-ChildItem "Q:\" -Force | Where-Object {
    $_.Name -ne "`$Recycle.Bin" -and $_.Name -notmatch "System Volume"
} | Sort-Object PSIsContainer -Descending | Sort-Object Name | ForEach-Object {
    $tag = if ($_.PSIsContainer) { "[D]" } else { "[F]" }
    Write-Host "  $tag $($_.Name)"
}
Write-Host "`nDone."
