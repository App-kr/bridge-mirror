$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Chrome Fix Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# === STEP 1: Download Chrome Enterprise MSI ===
Write-Host "`n[1/4] Downloading Chrome Enterprise installer..." -ForegroundColor Yellow

$msiPath = "$env:TEMP\ChromeEnterprise64.msi"
$url = "https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi"

try {
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($url, $msiPath)
    $size = (Get-Item $msiPath).Length / 1MB
    Write-Host "  Downloaded: $([math]::Round($size,1)) MB" -ForegroundColor Green
} catch {
    Write-Host "  FAILED: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Trying alternative download..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri $url -OutFile $msiPath -UseBasicParsing
        Write-Host "  Downloaded (alt method)" -ForegroundColor Green
    } catch {
        Write-Host "  Both methods failed. Exiting." -ForegroundColor Red
        exit 1
    }
}

# === STEP 2: Install Chrome System-Wide ===
Write-Host "`n[2/4] Installing Chrome to C:\Program Files (system-wide)..." -ForegroundColor Yellow

$result = Start-Process msiexec.exe -ArgumentList "/i `"$msiPath`" /qn /norestart ALLUSERS=1" -Wait -PassThru
if ($result.ExitCode -eq 0) {
    Write-Host "  Chrome installed successfully." -ForegroundColor Green
} else {
    Write-Host "  Install exit code: $($result.ExitCode)" -ForegroundColor Red
    if ($result.ExitCode -eq 1603) {
        Write-Host "  Hint: Run this script as Administrator." -ForegroundColor Yellow
    }
}

# Verify install
$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (Test-Path $chromePath) {
    $ver = (Get-Item $chromePath).VersionInfo.FileVersion
    Write-Host "  Verified: Chrome $ver at $chromePath" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Chrome not found at expected path." -ForegroundColor Red
}

# === STEP 3: Disable Problematic Startup Entries ===
Write-Host "`n[3/4] Disabling auto-start for banking security plugins..." -ForegroundColor Yellow

# These plugins don't need to run at startup.
# They activate on-demand when visiting banking/gov websites.
$disableKeys = @(
    @{Key="HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run";    Name="wizvera-veraport-x64"},
    @{Key="HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run";    Name="CrossEXService"},
    @{Key="HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run";    Name="MagicLine4NPIZ"}
)

foreach ($entry in $disableKeys) {
    try {
        $existing = Get-ItemProperty $entry.Key -Name $entry.Name -ErrorAction SilentlyContinue
        if ($existing) {
            $backupKey = $entry.Key -replace "\\Run$", "\Run_Disabled"
            if (-not (Test-Path $backupKey)) { New-Item $backupKey -Force | Out-Null }
            $val = $existing.($entry.Name)
            Set-ItemProperty $backupKey -Name $entry.Name -Value $val -ErrorAction SilentlyContinue
            Remove-ItemProperty $entry.Key -Name $entry.Name -ErrorAction Stop
            Write-Host "  Disabled: $($entry.Name)" -ForegroundColor Green
        } else {
            Write-Host "  Not found (already removed or not present): $($entry.Name)" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  Could not disable $($entry.Name): $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# === STEP 4: Add Chrome to Windows Defender Exclusions ===
Write-Host "`n[4/4] Adding Chrome to Windows Defender exclusions..." -ForegroundColor Yellow

try {
    Add-MpPreference -ExclusionPath "C:\Program Files\Google\Chrome" -ErrorAction Stop
    Write-Host "  Exclusion added for Chrome directory." -ForegroundColor Green
} catch {
    Write-Host "  Could not add exclusion (non-critical): $($_.Exception.Message)" -ForegroundColor Yellow
}

# === SUMMARY ===
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`nChrome install path:"
if (Test-Path $chromePath) {
    Write-Host "  OK: $chromePath" -ForegroundColor Green
} else {
    Write-Host "  NOT FOUND" -ForegroundColor Red
}

Write-Host "`nDisabled startup entries (safe to disable - load on-demand from websites):"
Write-Host "  - wizvera-veraport-x64 (Veraport)" -ForegroundColor Gray
Write-Host "  - CrossEXService (iniLINE CrossEX)" -ForegroundColor Gray
Write-Host "  - MagicLine4NPIZ (DreamSecurity)" -ForegroundColor Gray

Write-Host "`nKept active:"
Write-Host "  - AhnLab Safe Transaction (banking protection)" -ForegroundColor White

Write-Host "`nRECOMMENDED: Reboot and verify Chrome is still present." -ForegroundColor Yellow
Write-Host "If Chrome is deleted again after reboot, AhnLab Safe Transaction"
Write-Host "quarantine folder needs to be checked manually."

# Cleanup
Remove-Item $msiPath -ErrorAction SilentlyContinue
