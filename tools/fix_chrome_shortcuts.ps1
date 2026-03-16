# Chrome Shortcut Diagnosis and Fix Script
$ErrorActionPreference = 'SilentlyContinue'

# 1. Find Chrome installation
$chromePaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$chromeExe = $null
foreach ($p in $chromePaths) {
    if (Test-Path $p) {
        $chromeExe = $p
        Write-Host "[OK] chrome.exe: $p"
        break
    }
}
if (-not $chromeExe) {
    Write-Host "[WARN] chrome.exe NOT FOUND - Chrome may not be installed"
}

# 2. Find chrome_proxy.exe
$proxyPaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome_proxy.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome_proxy.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome_proxy.exe"
)

$proxyExe = $null
foreach ($p in $proxyPaths) {
    if (Test-Path $p) {
        $proxyExe = $p
        Write-Host "[OK] chrome_proxy.exe: $p"
        break
    }
}
if (-not $proxyExe) {
    Write-Host "[MISSING] chrome_proxy.exe NOT FOUND"
}

# 3. Scan for broken Chrome shortcuts
$searchDirs = @(
    "$env:USERPROFILE\Desktop",
    "C:\Users\Public\Desktop",
    "C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs",
    "$env:APPDATA\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"
)

Write-Host ""
Write-Host "[SCAN] Scanning Chrome shortcuts..."
$shell = New-Object -ComObject WScript.Shell
$brokenShortcuts = @()

foreach ($dir in $searchDirs) {
    if (-not (Test-Path $dir)) { continue }
    $lnkFiles = Get-ChildItem $dir -Filter "*.lnk" -Recurse
    foreach ($lnk in $lnkFiles) {
        try {
            $sc = $shell.CreateShortcut($lnk.FullName)
            $target = $sc.TargetPath
            if ($target -like "*chrome*") {
                Write-Host "  LNK: $($lnk.FullName)"
                Write-Host "  TGT: $target"
                if (-not (Test-Path $target)) {
                    Write-Host "  -> [BROKEN] target missing"
                    $brokenShortcuts += $lnk.FullName
                } else {
                    Write-Host "  -> [OK]"
                }
            }
        } catch {}
    }
}

# 4. Fix broken shortcuts
if ($brokenShortcuts.Count -gt 0 -and $chromeExe) {
    Write-Host ""
    Write-Host "[FIX] Fixing broken shortcuts..."
    foreach ($lnkPath in $brokenShortcuts) {
        try {
            $sc = $shell.CreateShortcut($lnkPath)
            $sc.TargetPath = $chromeExe
            $sc.IconLocation = "$chromeExe,0"
            $sc.Save()
            Write-Host "  [FIXED] $lnkPath"
        } catch {
            Write-Host "  [FAIL] $lnkPath"
        }
    }
} elseif ($brokenShortcuts.Count -gt 0) {
    Write-Host ""
    Write-Host "[ERROR] Chrome not installed - reinstall Chrome first"
} else {
    Write-Host ""
    Write-Host "[INFO] No broken Chrome shortcuts found"
}

# 5. Check Windows Defender quarantine
Write-Host ""
Write-Host "[DEFENDER] Checking quarantine..."
try {
    $quarantine = Get-MpThreatDetection | Where-Object { $_.Resources -like "*chrome*" }
    if ($quarantine) {
        Write-Host "[FOUND] Defender quarantined Chrome-related files:"
        $quarantine | Select-Object ThreatName, ActionSuccess, Resources | Format-List
    } else {
        Write-Host "[OK] No Chrome files in Defender quarantine"
    }
} catch {
    Write-Host "[SKIP] Cannot query Defender"
}

Write-Host ""
Write-Host "Done."
