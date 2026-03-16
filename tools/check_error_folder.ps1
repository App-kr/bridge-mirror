$items = Get-ChildItem "Q:\" -ErrorAction SilentlyContinue
foreach ($item in $items) {
    if ($item.LastWriteTime -gt (Get-Date).AddHours(-2) -and $item.Name -notmatch "^bridge base|^Claudework") {
        Write-Host "RECENT: $($item.Name)"
        if ($item.PSIsContainer) {
            Get-ChildItem $item.FullName -ErrorAction SilentlyContinue | Select-Object Name, FullName, Extension, Length | Format-Table
        }
    }
}
