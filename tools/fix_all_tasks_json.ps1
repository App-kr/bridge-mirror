$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Scanning all Q-drive .vscode/tasks.json for runOn:folderOpen ==="
$found = 0
$patched = 0
Get-ChildItem "Q:\" -Recurse -Filter "tasks.json" -ErrorAction SilentlyContinue -Force |
    Where-Object { $_.FullName -like '*\.vscode\*' -and $_.FullName -notlike '*\node_modules\*' } |
    ForEach-Object {
        $found++
        $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
        if (-not $content) { return }
        if ($content -match 'folderOpen') {
            Write-Host ("  PATCH NEEDED: {0}" -f $_.FullName)
            $bak = "$($_.FullName).bak.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
            Copy-Item $_.FullName $bak -Force
            # runOn 옵션 제거 (object 형태와 string 형태 둘 다)
            $newContent = $content -replace '"runOptions"\s*:\s*\{\s*"runOn"\s*:\s*"folderOpen"\s*\}\s*,?\s*', ''
            $newContent = $newContent -replace ',\s*"runOptions"\s*:\s*\{\s*"runOn"\s*:\s*"folderOpen"\s*\}', ''
            $newContent | Out-File -FilePath $_.FullName -Encoding utf8 -Force
            Write-Host ("    PATCHED (backup: {0})" -f $bak)
            $patched++
        } else {
            Write-Host ("  OK: {0}" -f $_.FullName)
        }
    }
Write-Host ""
Write-Host ("Found {0} tasks.json, patched {1}" -f $found, $patched)

Write-Host ""
Write-Host "=== Killing all auto-spawned 'claude --model' powershell instances ==="
$killed = 0
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
    Where-Object {
        $_.CommandLine -match 'cd\s+Q:\\Claudework.*claude\s+--model' -or
        $_.CommandLine -match 'cd Q:\\Claudework; claude'
    } |
    ForEach-Object {
        Write-Host ("  KILL PID={0}" -f $_.ProcessId)
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        $killed++
    }
Write-Host ("Killed {0} auto-spawned powershell instances" -f $killed)

Write-Host ""
Write-Host "=== Final verification (10s) ==="
Start-Sleep -Seconds 5
$still = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
    Where-Object { $_.CommandLine -match 'claude --model' }
Write-Host ("  Remaining 'claude --model' powershell: {0}" -f $still.Count)
