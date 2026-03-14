# Check old bridge directory and WSH sources

Write-Host "--- bridge dir files (no extension) ---"
Get-ChildItem "Q:\Claudework\bridge" -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -eq '' -and -not $_.PSIsContainer } |
    Select-Object FullName, Length, LastWriteTime

Write-Host "--- bridge dir ALL files ---"
Get-ChildItem "Q:\Claudework\bridge" -Recurse -ErrorAction SilentlyContinue |
    Select-Object FullName, Extension, LastWriteTime | Sort-Object LastWriteTime -Descending

Write-Host "--- Q:\Claudework vbs/js files ---"
Get-ChildItem "Q:\Claudework" -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -match 'vbs|vbe|js|jse|wsf' -or $_.Extension -eq '' } |
    Select-Object Name, Extension, FullName

Write-Host "--- Run registry bridge entries ---"
@("HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
  "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run") | ForEach-Object {
    $k = Get-ItemProperty $_ -ErrorAction SilentlyContinue
    if ($k) {
        $k.PSObject.Properties | Where-Object { $_.Name -notmatch "^PS" -and $_.Value -match "bridge" } | ForEach-Object {
            Write-Host "  $($_.Name) = $($_.Value)"
        }
    }
}

Write-Host "--- wscript/cscript processes ---"
Get-Process | Where-Object { $_.Name -match "wscript|cscript" } | Select-Object Id, Name, Path
