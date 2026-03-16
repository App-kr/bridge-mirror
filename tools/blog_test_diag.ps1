$ErrorActionPreference = 'SilentlyContinue'

Write-Host "=== BRIDGE BLOG AUTOMATION - TEST DIAGNOSIS ==="
Write-Host ""

# 1. Disk space
$drive = Get-PSDrive Q
$freeGB = [math]::Round($drive.Free/1GB, 1)
$usedGB = [math]::Round($drive.Used/1GB, 1)
Write-Host "[DISK] Q Drive - Used: ${usedGB}GB / Free: ${freeGB}GB"
if ($freeGB -lt 1) { Write-Host "[WARN] Disk space critically low!" }

# 2. _tmp_resized leftover
$tmpDir = "Q:\Claudework\ClaudeBlog\images\_tmp_resized"
$tmpFiles = Get-ChildItem $tmpDir -ErrorAction SilentlyContinue
if ($tmpFiles -and $tmpFiles.Count -gt 0) {
    $sizeMB = [math]::Round(($tmpFiles | Measure-Object Length -Sum).Sum / 1MB, 2)
    Write-Host "[WARN] _tmp_resized: $($tmpFiles.Count) leftover files (${sizeMB}MB) - cleanup needed"
} else {
    Write-Host "[OK]  _tmp_resized: clean"
}

# 3. Python environment
Write-Host ""
Write-Host "=== Python Environment ==="
$pyPaths = @(
    "C:\Python314\python.exe",
    "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe",
    "Q:\Claudework\ClaudeBlog\.venv\Scripts\python.exe"
)
foreach ($py in $pyPaths) {
    if (Test-Path $py) {
        $ver = & $py --version 2>&1
        $enc = & $py -c "import encodings; print('enc OK')" 2>&1
        Write-Host "  $py"
        Write-Host "  Version: $ver | Encodings: $enc"
    }
}

# 4. Key packages on Python314 (primary)
Write-Host ""
Write-Host "=== Package Check (C:\Python314) ==="
$py314 = "C:\Python314\python.exe"
if (Test-Path $py314) {
    $pkgs = @("anthropic","selenium","schedule","PIL","json_repair","google.genai","pyperclip","cryptography","keyring","dotenv")
    foreach ($pkg in $pkgs) {
        $r = & $py314 -c "import $pkg; print('OK')" 2>&1
        $status = if ($r -match "OK") { "[OK]" } else { "[MISSING]" }
        Write-Host "  $status $pkg"
    }
}

# 5. secrets.enc + keyring
Write-Host ""
Write-Host "=== Secrets Check ==="
if (Test-Path "Q:\Claudework\ClaudeBlog\secrets.enc") {
    Write-Host "[OK]  secrets.enc EXISTS"
} else {
    Write-Host "[FAIL] secrets.enc MISSING"
}
$keyringCheck = & "C:\Python314\python.exe" -c "import keyring; k=keyring.get_password('BridgeBlogAuto','master_key'); print('KEYRING_SET' if k else 'KEYRING_EMPTY')" 2>&1
Write-Host "  Keyring: $keyringCheck"

# 6. blog_history.db
Write-Host ""
Write-Host "=== blog_history.db ==="
$dbPath = "Q:\Claudework\ClaudeBlog\logs\blog_history.db"
if (Test-Path $dbPath) {
    $sizKB = [math]::Round((Get-Item $dbPath).Length / 1KB, 1)
    Write-Host "[OK]  blog_history.db exists (${sizKB}KB)"
} else {
    Write-Host "[FAIL] blog_history.db MISSING"
}

# 7. Image folders
Write-Host ""
Write-Host "=== Image Folders ==="
$imgFolders = @("강사", "원어민수업", "bridge")
foreach ($folder in $imgFolders) {
    $path = "Q:\Claudework\ClaudeBlog\images\$folder"
    $imgs = Get-ChildItem $path -Include "*.jpg","*.jpeg","*.png","*.JPG","*.PNG","*.webp" -Recurse -ErrorAction SilentlyContinue
    $count = if ($imgs) { $imgs.Count } else { 0 }
    $status = if ($count -gt 0) { "[OK]" } else { "[WARN]" }
    Write-Host "  $status images/$folder : $count files"
}

# 8. recent dry_outputs
Write-Host ""
Write-Host "=== Recent dry_outputs ==="
$dryFiles = Get-ChildItem "Q:\Claudework\ClaudeBlog\dry_outputs" -Filter "*.txt" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 3
if ($dryFiles) {
    foreach ($f in $dryFiles) {
        Write-Host "  $($f.Name)  [$($f.LastWriteTime.ToString('yyyy-MM-dd HH:mm'))]"
    }
} else {
    Write-Host "  None"
}

# 9. existing test file
Write-Host ""
Write-Host "=== Test Files ==="
$testFiles = Get-ChildItem "Q:\Claudework\ClaudeBlog\tests" -ErrorAction SilentlyContinue
foreach ($t in $testFiles) {
    Write-Host "  $($t.Name)"
}

Write-Host ""
Write-Host "=== DIAGNOSIS COMPLETE ==="
