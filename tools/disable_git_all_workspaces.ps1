$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

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

$snippet = @'
{
  "_comment": "2026-05-10: git.enabled=false to eliminate IDE-side git console flicker. Use Claude Code CLI / bash for git ops.",
  "git.enabled": false,
  "git.autorefresh": false,
  "git.autoRepositoryDetection": false,
  "git.decorations.enabled": false,
  "git.repositoryScanIgnoredFolders": ["**/*"],
  "git.repositoryScanMaxDepth": 0,
  "scm.autoReveal": false,
  "scm.alwaysShowProviders": false,
  "scm.providers.visible": 0,
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

$applied = 0
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
    $snippet | Out-File -FilePath $sFile -Encoding utf8 -Force
    Write-Host ("APPLIED git.enabled=false: " + $sFile)
    $applied++
}
Write-Host ""
Write-Host ("Total: " + $applied + " workspaces")
Write-Host ""
Write-Host "USER ACTION: Restart Antigravity to apply (Ctrl+Shift+P > Reload Window)"
