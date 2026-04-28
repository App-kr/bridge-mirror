$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$settingsContent = @'
{
  "_comment": "Antigravity/VS Code workspace - disable git polling (auto-applied 2026-04-28)",
  "git.autorefresh": false,
  "git.autoRepositoryDetection": false,
  "git.decorations.enabled": false,
  "scm.autoReveal": false,
  "scm.alwaysShowProviders": false,
  "files.watcherExclude": {
    "**/.git/**": true,
    "**/node_modules/**": true,
    "**/.venv/**": true,
    "**/dist/**": true,
    "**/.next/**": true,
    "**/build/**": true
  }
}
'@

# 모든 활성 워크스페이스 (Antigravity workspaceStorage 에서 추출한 Q드라이브 폴더들)
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
    "Q:\Codex testing",
    "Q:\bridge-overnight"
)

Write-Host "=== Applying .vscode/settings.json to all Q-drive workspaces ==="
$applied = 0
$skipped = 0
foreach ($ws in $workspaces) {
    if (-not (Test-Path $ws)) {
        $skipped++
        continue
    }
    $vscDir = Join-Path $ws ".vscode"
    if (-not (Test-Path $vscDir)) {
        New-Item -ItemType Directory -Force -Path $vscDir | Out-Null
    }
    $sFile = Join-Path $vscDir "settings.json"
    if (Test-Path $sFile) {
        # 이미 있으면 백업 후 덮어쓰기 (사용자 설정 보호)
        $bak = "$sFile.bak.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        try {
            $existing = Get-Content $sFile -Raw -ErrorAction Stop
            if ($existing -match 'git\.autorefresh') {
                Write-Host ("  ALREADY-OK: {0}" -f $sFile)
                continue
            }
            Copy-Item $sFile $bak -Force
            Write-Host ("  BACKUP: {0}" -f $bak)
        } catch {}
    }
    $settingsContent | Out-File -FilePath $sFile -Encoding utf8 -Force
    Write-Host ("  APPLIED: {0}" -f $sFile)
    $applied++
}
Write-Host ""
Write-Host ("Result: {0} applied, {1} skipped (folder not found)" -f $applied, $skipped)

Write-Host ""
Write-Host "=== Global git config changes (system-wide, all repos) ==="
& git config --global core.fsmonitor false 2>&1 | Out-Null
Write-Host "  git config --global core.fsmonitor false"
& git config --global gc.auto 0 2>&1 | Out-Null
Write-Host "  git config --global gc.auto 0  (no auto garbage collection)"
& git config --global feature.manyFiles true 2>&1 | Out-Null
Write-Host "  git config --global feature.manyFiles true  (faster status)"

Write-Host ""
Write-Host "=== Verify global config ==="
& git config --global --list 2>&1 | Select-String -Pattern 'fsmonitor|gc\.auto|feature' | ForEach-Object { Write-Host ("  {0}" -f $_) }
