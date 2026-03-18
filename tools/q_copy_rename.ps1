$ErrorActionPreference = "SilentlyContinue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$target = "Q:\images_sojin_school"
$garbled = Get-ChildItem "Q:\" -Force -Directory | Where-Object {
    ($_.Name -replace '[^\x20-\x7E]', '').Length -ne $_.Name.Length
}

if ($garbled.Count -eq 0) {
    Write-Host "No garbled folders found - already clean!"
    exit
}

foreach ($d in $garbled) {
    Write-Host "Source: [$($d.Name)]"
    $src = $d.FullName

    if (-not (Test-Path $target)) {
        New-Item -Path $target -ItemType Directory | Out-Null
    }

    # Copy all files using robocopy (handles locked folders better)
    $result = robocopy $src $target /E /COPYALL /R:2 /W:1 /NP /NFL /NDL 2>&1
    Write-Host "  Robocopy exit: $LASTEXITCODE"

    # Try to remove original
    $rem = Remove-Item -LiteralPath $src -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $src) {
        Write-Host "  WARNING: Original still exists (locked) - contents copied to $target"
        Write-Host "  Manually delete [$($d.Name)] later if needed"
    } else {
        Write-Host "  Original deleted successfully"
    }
}

Write-Host "`n=== FINAL Q:\ ==="
Get-ChildItem "Q:\" -Force | Where-Object {
    $_.Name -ne "`$Recycle.Bin" -and $_.Name -notmatch "System Volume"
} | Sort-Object Name | ForEach-Object {
    $tag = if ($_.PSIsContainer) { "[D]" } else { "[F]" }
    Write-Host "  $tag $($_.Name)"
}
