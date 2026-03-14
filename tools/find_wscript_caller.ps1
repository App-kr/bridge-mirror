# Find all files that call wscript.exe with unquoted bridge paths

Write-Host "--- All .vbs files calling bridge path ---"
Get-ChildItem "Q:\" -Recurse -Include "*.vbs","*.bat","*.cmd","*.ps1" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "_BACKUP|backups|__pycache__" } |
    Select-String -Pattern "wscript.*bridge|bridge.*wscript" -CaseSensitive:$false -ErrorAction SilentlyContinue |
    Select-Object Path, LineNumber, Line | Format-Table -Wrap

Write-Host "--- start_craig.vbs content (Claudework root) ---"
Get-Content "Q:\Claudework\start_craig.vbs" -ErrorAction SilentlyContinue

Write-Host "--- BridgeCraig folder ---"
Get-ChildItem "Q:\BridgeCraig" -ErrorAction SilentlyContinue | Select-Object Name, Extension

Write-Host "--- All .vbs files on Q drive ---"
Get-ChildItem "Q:\" -Recurse -Include "*.vbs" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "_BACKUP|backups" } |
    Select-Object FullName, LastWriteTime
