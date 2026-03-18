$ErrorActionPreference = "SilentlyContinue"
$skip = @('System Volume Information', '$Recycle.Bin', 'Claudework')

Get-ChildItem "Q:\" -Force -Directory | Where-Object {
    $_.Name -notin $skip -and $_.Name -ne 'System Volume Information'
} | ForEach-Object {
    $size = (Get-ChildItem $_.FullName -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    $sizeMB = [math]::Round($size / 1MB, 1)
    [PSCustomObject]@{
        Name     = $_.Name
        MB       = $sizeMB
        Modified = $_.LastWriteTime.ToString("MM-dd HH:mm")
    }
} | Sort-Object MB -Descending | Format-Table -AutoSize
