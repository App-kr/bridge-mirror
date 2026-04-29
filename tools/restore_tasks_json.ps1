$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Restoring tasks.json from .bak files ==="
Get-ChildItem "Q:\" -Recurse -Filter "tasks.json.bak.*" -ErrorAction SilentlyContinue -Force |
    Where-Object { $_.FullName -like '*\.vscode\*' } |
    Sort-Object FullName -Descending |
    ForEach-Object {
        $orig = $_.FullName -replace '\.bak\.\d+_\d+$', ''
        Copy-Item $_.FullName $orig -Force
        Write-Host ("  RESTORED: {0}" -f $orig)
    }

Write-Host ""
Write-Host "=== Verify Q:\Claudework\.vscode\tasks.json ==="
Get-Content "Q:\Claudework\.vscode\tasks.json" | Select-String -Pattern "folderOpen" | ForEach-Object { Write-Host ("  {0}" -f $_) }
