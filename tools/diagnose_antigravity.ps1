$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== A) Antigravity processes - RAM/CPU ==="
$ag = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '*Antigravity*' }
$totalRam = 0
$ag | ForEach-Object {
    $ram = [math]::Round($_.WorkingSetSize/1MB, 1)
    $totalRam += $ram
    $type = ''
    if ($_.CommandLine -match '--type=([\w-]+)') { $type = $matches[1] }
    if ($_.CommandLine -match '--utility-sub-type=([\w\.]+)') { $type += " ($($matches[1]))" }
    [PSCustomObject]@{
        PID = $_.ProcessId
        RAM_MB = $ram
        Type = $type
    }
} | Sort-Object RAM_MB -Descending | Format-Table -AutoSize

Write-Host ("`n  TOTAL Antigravity RAM: {0} MB ({1} processes)" -f $totalRam, $ag.Count)

Write-Host ""
Write-Host "=== B) LSP / TypeScript / Pyright servers (extension processes) ==="
$lsp = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^(node|tsserver|pyright|pylsp|gopls|rust-analyzer|clangd)\.exe$' -and
    $_.CommandLine -notlike '*claude-code*' -and
    ($_.ParentProcessId -in ($ag | Select-Object -ExpandProperty ProcessId))
}
if ($lsp) {
    $lsp | Select-Object ProcessId, Name, @{N='RAM_MB';E={[math]::Round($_.WorkingSetSize/1MB,1)}}, @{N='cmd';E={if($_.CommandLine){$_.CommandLine.Substring(0,[Math]::Min(120,$_.CommandLine.Length))}else{''}}} | Format-Table -AutoSize -Wrap
} else {
    Write-Host "  (no LSP servers detected as Antigravity children)"
}

Write-Host ""
Write-Host "=== C) Workspace storage size (heavy = remembered open folders) ==="
$wsStore = "$env:APPDATA\Antigravity\User\workspaceStorage"
if (Test-Path $wsStore) {
    $folders = Get-ChildItem $wsStore -Directory -ErrorAction SilentlyContinue
    Write-Host ("  Total workspace folders: {0}" -f $folders.Count)
    $folders | ForEach-Object {
        $size = (Get-ChildItem $_.FullName -Recurse -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
        $wsJson = Join-Path $_.FullName "workspace.json"
        $folder = ''
        if (Test-Path $wsJson) {
            try {
                $folder = (Get-Content $wsJson -Raw | ConvertFrom-Json).folder
            } catch {}
        }
        [PSCustomObject]@{
            SizeMB = [math]::Round($size/1MB, 1)
            Folder = $folder
        }
    } | Sort-Object SizeMB -Descending | Select-Object -First 10 | Format-Table -AutoSize
}

Write-Host ""
Write-Host "=== D) Restore-on-startup setting ==="
$settings = "$env:APPDATA\Antigravity\User\settings.json"
if (Test-Path $settings) {
    $content = Get-Content $settings -Raw -ErrorAction SilentlyContinue
    if ($content -match '"window\.restoreWindows"') {
        Write-Host "  $(($content | Select-String -Pattern '"window\.restoreWindows".*').Matches.Value)"
    } else {
        Write-Host "  window.restoreWindows: NOT SET (default = preserve all = heavy restore)"
    }
    if ($content -match '"window\.openFoldersInNewWindow"') {
        Write-Host "  $(($content | Select-String -Pattern '"window\.openFoldersInNewWindow".*').Matches.Value)"
    }
}

Write-Host ""
Write-Host "=== E) Top-3 RAM consumers (system-wide) ==="
Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 5 |
    Select-Object Name, Id, @{N='RAM_MB';E={[math]::Round($_.WorkingSet/1MB,1)}} |
    Format-Table -AutoSize
