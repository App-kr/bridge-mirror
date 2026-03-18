$ErrorActionPreference = "SilentlyContinue"

# 한글 깨진 폴더 내부 확인
Write-Host "=== Garbled folder contents ==="
Get-ChildItem "Q:\" -Force -Directory | Where-Object { $_.Name -match "[^\x20-\x7E]" -or $_.Name -like "*'*" } | ForEach-Object {
    Write-Host "`n[$($_.Name)]"
    Get-ChildItem $_.FullName -Force -ErrorAction SilentlyContinue | Select-Object Name, Length | Format-Table -AutoSize
}

# 0MB 폴더 내부 확인
Write-Host "`n=== Zero-size folders (internal check) ==="
$zeroFolders = @('_SECURITY_QUARANTINE', 'Acrobat Pro', 'Filezilla', '_REPORTS', 'intake', 'NPKI', 'Calendar', 'Claudeother', 'data', '_REPORTS', 'Headset')
foreach ($f in $zeroFolders) {
    $path = "Q:\$f"
    if (Test-Path $path) {
        $items = Get-ChildItem $path -Force -ErrorAction SilentlyContinue
        Write-Host "  [$f] : $($items.Count) items"
        $items | Select-Object -First 5 | ForEach-Object { Write-Host "    - $($_.Name)" }
    }
}

# bridge-overnight 내부 확인
Write-Host "`n=== bridge-overnight top-level ==="
Get-ChildItem "Q:\bridge-overnight" -Force -ErrorAction SilentlyContinue | Select-Object Name, LastWriteTime | Format-Table -AutoSize

# .backups vs _BACKUPS 내부 확인
Write-Host "`n=== .backups top-level ==="
Get-ChildItem "Q:\.backups" -Force -ErrorAction SilentlyContinue | Select-Object Name | Format-Table -AutoSize

Write-Host "`n=== _BACKUPS top-level ==="
Get-ChildItem "Q:\_BACKUPS" -Force -ErrorAction SilentlyContinue | Select-Object Name | Format-Table -AutoSize

# Claudeother, data, Codex testing
Write-Host "`n=== Claudeother ==="
Get-ChildItem "Q:\Claudeother" -Force -Recurse -ErrorAction SilentlyContinue | Select-Object FullName | Format-Table -AutoSize

Write-Host "`n=== BridgeCraig top-level ==="
Get-ChildItem "Q:\BridgeCraig" -Force -ErrorAction SilentlyContinue | Select-Object Name, LastWriteTime | Format-Table -AutoSize
