$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 메모리 + CPU 절약 강화 settings (이전 git polling 차단 + 메모리 제한)
$settingsContent = @'
{
  "_comment": "Antigravity/VS Code workspace - safe memory & CPU optimization (auto-applied 2026-04-28)",
  "git.autorefresh": false,
  "git.autoRepositoryDetection": false,
  "git.decorations.enabled": false,
  "scm.autoReveal": false,
  "scm.alwaysShowProviders": false,
  "files.watcherExclude": {
    "**/.git/**": true,
    "**/node_modules/**": true,
    "**/.venv/**": true,
    "**/venv/**": true,
    "**/__pycache__/**": true,
    "**/dist/**": true,
    "**/.next/**": true,
    "**/build/**": true,
    "**/.snapshots/**": true,
    "**/.backups/**": true,
    "**/logs/**": true,
    "**/*.pyc": true
  },
  "search.exclude": {
    "**/.git": true,
    "**/node_modules": true,
    "**/.venv": true,
    "**/venv": true,
    "**/__pycache__": true,
    "**/dist": true,
    "**/.next": true,
    "**/build": true,
    "**/.snapshots": true,
    "**/.backups": true,
    "**/logs": true
  },
  "search.followSymlinks": false,
  "search.useIgnoreFiles": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  },
  "typescript.tsserver.maxTsServerMemory": 2048,
  "typescript.disableAutomaticTypeAcquisition": true,
  "typescript.tsserver.watchOptions": {
    "watchFile": "useFsEventsOnParentDirectory",
    "fallbackPolling": "dynamicPriority"
  },
  "python.analysis.indexing": false,
  "python.analysis.autoImportCompletions": false,
  "telemetry.telemetryLevel": "off"
}
'@

$workspaces = @(
    "Q:\",
    "Q:\Claudework",
    "Q:\Claudework\bridge base",
    "Q:\Claudework\bridge",
    "Q:\Claudework\FBAutowork",
    "Q:\Claudework\ClaudeBlog",
    "Q:\Claudework\matjokdo_safe",
    "Q:\Claudework\wealth_manager",
    "Q:\Claudework\bridge_ads",
    "Q:\Claudework\agentic_os",
    "Q:\bridge-overnight"
)

Write-Host "=== Updating .vscode/settings.json with memory savings (Q-drive only) ==="
$updated = 0
foreach ($ws in $workspaces) {
    if (-not (Test-Path $ws)) { continue }
    $vscDir = Join-Path $ws ".vscode"
    if (-not (Test-Path $vscDir)) {
        New-Item -ItemType Directory -Force -Path $vscDir | Out-Null
    }
    $sFile = Join-Path $vscDir "settings.json"

    if (Test-Path $sFile) {
        $bak = "$sFile.bak.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Copy-Item $sFile $bak -Force
    }
    $settingsContent | Out-File -FilePath $sFile -Encoding utf8 -Force
    Write-Host ("  UPDATED: {0}" -f $sFile)
    $updated++
}
Write-Host ""
Write-Host ("Result: {0} workspace settings updated (Q-drive only, IC-04 safe)" -f $updated)

Write-Host ""
Write-Host "=== Idle Next.js dev server check (kill if user not using) ==="
$nextDevs = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -match 'next.*dev|npm.*run.*dev|node.*next' -and
    $_.WorkingSetSize -gt 200MB
}
if ($nextDevs) {
    Write-Host "Found Next.js dev servers (200MB+):"
    $nextDevs | Select-Object ProcessId, @{N='RAM_MB';E={[math]::Round($_.WorkingSetSize/1MB,1)}}, @{N='age_min';E={[math]::Round(((Get-Date)-$_.CreationDate).TotalMinutes,1)}} | Format-Table -AutoSize
    Write-Host "  (Not auto-killed - user may be working. RAMWatchdog will clean idle ones in 30min.)"
} else {
    Write-Host "  No idle Next.js dev servers"
}

Write-Host ""
Write-Host "=== Memory snapshot ==="
$os = Get-CimInstance Win32_OperatingSystem
$used = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB, 1)
$total = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
Write-Host ("  RAM: {0} GB / {1} GB ({2}%)" -f $used, $total, [math]::Round($used/$total*100,1))
