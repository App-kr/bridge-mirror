$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Find the Korean folder by scanning Q:\
$all = Get-ChildItem "Q:\" -Force -Directory
$garbled = $all | Where-Object {
    ($_.Name -replace '[^\x20-\x7E]', '').Length -ne $_.Name.Length
}

if ($garbled.Count -eq 0) {
    Write-Host "No garbled folders found."
    exit
}

foreach ($d in $garbled) {
    Write-Host "Processing: [$($d.Name)] at $($d.FullName)"
    $target = "Q:\images_sojin_school"
    if (Test-Path $target) {
        Write-Host "  Target already exists: $target"
    } else {
        try {
            # Use LiteralPath to handle special characters
            Rename-Item -LiteralPath $d.FullName -NewName "images_sojin_school" -Force
            Write-Host "  SUCCESS: renamed to images_sojin_school"
        } catch {
            Write-Host "  FAILED: $($_.Exception.Message)"
            # Try cmd /c ren as fallback
            Write-Host "  Trying cmd ren..."
            $src = $d.FullName
            cmd /c "ren ""$src"" images_sojin_school" 2>&1
            Write-Host "  cmd exit: $LASTEXITCODE"
        }
    }
}

Write-Host "`nCurrent Q:\ contents:"
Get-ChildItem "Q:\" -Force | Where-Object {
    $_.Name -ne "`$Recycle.Bin" -and $_.Name -notmatch "System Volume"
} | Sort-Object Name | ForEach-Object {
    Write-Host "  $($_.Name)"
}
