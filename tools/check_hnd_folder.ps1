# Check 'HND'H% folder properly
$items = Get-ChildItem "Q:\" -ErrorAction SilentlyContinue
$hnd = $items | Where-Object { $_.Name -like "*HND*" }

if ($hnd) {
    Write-Host "Found: $($hnd.Name)"
    Write-Host "FullName: $($hnd.FullName)"
    Write-Host "Attributes: $($hnd.Attributes)"
    Write-Host "Is ReparsePoint: $(($hnd.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)"
    Write-Host "LastWriteTime: $($hnd.LastWriteTime)"
    Write-Host ""

    # Check if it's a junction/symlink
    $dirInfo = [System.IO.Directory]::GetFiles($hnd.FullName, "*", [System.IO.SearchOption]::TopDirectoryOnly)
    Write-Host "Files inside count: $($dirInfo.Count)"

    $childItems = Get-ChildItem $hnd.FullName -ErrorAction SilentlyContinue -Force | Select-Object -First 10
    Write-Host "Direct children:"
    $childItems | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize
} else {
    Write-Host "No HND folder found in Q:\"
}
