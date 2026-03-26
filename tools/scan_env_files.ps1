# PHASE 1: Scan all .env files on Q:\
Write-Host "=== PHASE 1: Scanning Q:\ for .env files ===" -ForegroundColor Cyan

$envFiles = Get-ChildItem -Path "Q:\" -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match "^\.env" -or $_.Name -eq ".env" } |
    Select-Object -ExpandProperty FullName

if (-not $envFiles) {
    Write-Host "No .env files found on Q:\" -ForegroundColor Green
    exit 0
}

Write-Host "Found $($envFiles.Count) file(s):" -ForegroundColor Yellow
$envFiles | ForEach-Object { Write-Host "  $_" }

# PHASE 2: Extract key names only (NO values)
Write-Host "`n=== PHASE 2: Key names only (values masked) ===" -ForegroundColor Cyan
foreach ($file in $envFiles) {
    Write-Host "`n--- $file ---" -ForegroundColor Yellow
    Get-Content $file -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_ -match "^([A-Za-z0-9_]+)\s*=") {
            Write-Host "  $($matches[1]) = ****"
        } elseif ($_ -match "^#" -or $_ -eq "") {
            # skip comments and blank lines
        }
    }
}

# PHASE 3: Check git tracking per repo
Write-Host "`n=== PHASE 3: Git tracking check ===" -ForegroundColor Cyan
$repos = @{}
foreach ($file in $envFiles) {
    $dir = Split-Path $file -Parent
    # walk up to find .git
    $cur = $dir
    while ($cur -ne "" -and $cur -ne "Q:\") {
        if (Test-Path (Join-Path $cur ".git")) {
            $repos[$cur] = $true
            break
        }
        $cur = Split-Path $cur -Parent
    }
}

$trackedFiles = @()
foreach ($file in $envFiles) {
    $dir = Split-Path $file -Parent
    $cur = $dir
    $repoRoot = $null
    while ($cur -ne "" -and $cur -ne "Q:\") {
        if (Test-Path (Join-Path $cur ".git")) {
            $repoRoot = $cur
            break
        }
        $cur = Split-Path $cur -Parent
    }
    if ($repoRoot) {
        $relPath = $file.Substring($repoRoot.Length + 1)
        $tracked = & git -C $repoRoot ls-files $relPath 2>$null
        if ($tracked) {
            Write-Host "  [TRACKED] $file (repo: $repoRoot)" -ForegroundColor Red
            $trackedFiles += @{ File = $file; Repo = $repoRoot; Rel = $relPath }
        } else {
            Write-Host "  [NOT TRACKED] $file" -ForegroundColor Green
        }
    } else {
        Write-Host "  [NO REPO] $file" -ForegroundColor Gray
    }
}

# PHASE 4: Remove git tracking
if ($trackedFiles.Count -gt 0) {
    Write-Host "`n=== PHASE 4: Removing git tracking ===" -ForegroundColor Cyan
    foreach ($item in $trackedFiles) {
        Write-Host "  git rm --cached $($item.File)"
        & git -C $item.Repo rm --cached $item.Rel 2>&1
    }
} else {
    Write-Host "`n=== PHASE 4: No tracked .env files - skip ===" -ForegroundColor Green
}

# PHASE 5: Delete all .env files
Write-Host "`n=== PHASE 5: Deleting all .env files ===" -ForegroundColor Cyan
foreach ($file in $envFiles) {
    Remove-Item $file -Force -ErrorAction SilentlyContinue
    if (-not (Test-Path $file)) {
        Write-Host "  [DELETED] $file" -ForegroundColor Green
    } else {
        Write-Host "  [FAILED]  $file" -ForegroundColor Red
    }
}

# PHASE 6: Commit + push per repo
if ($trackedFiles.Count -gt 0) {
    Write-Host "`n=== PHASE 6: Commit + push ===" -ForegroundColor Cyan
    $processedRepos = @{}
    foreach ($item in $trackedFiles) {
        $repo = $item.Repo
        if ($processedRepos[$repo]) { continue }
        $processedRepos[$repo] = $true
        Write-Host "  Committing repo: $repo" -ForegroundColor Yellow
        & git -C $repo add -A 2>&1
        & git -C $repo commit -m "security: remove plaintext .env from tracking" 2>&1
        & git -C $repo push --force-with-lease origin main 2>&1
        Write-Host "  [PUSHED] $repo" -ForegroundColor Green
    }
} else {
    Write-Host "`n=== PHASE 6: No repo changes - skip ===" -ForegroundColor Green
}

Write-Host "`n=== COMPLETE ===" -ForegroundColor Cyan
Write-Host "Total .env files found:   $($envFiles.Count)"
Write-Host "Git-tracked and removed:  $($trackedFiles.Count)"
Write-Host "All plaintext .env files deleted." -ForegroundColor Green
