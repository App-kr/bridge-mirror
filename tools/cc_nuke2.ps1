$ErrorActionPreference = "SilentlyContinue"
Write-Host "Adobe Creative Suite - Block All Updates"

# 1. Kill update processes
$killProcs = @("AdobeRefreshManager","ppmtool","ppml","CCXProcess","CCLibrary",
    "AdobeIPCBroker","CoreSync","AdobeDesktopService","AcroTray",
    "AdobeNotificationClient","AdobeCollabSync","AdobeGenuineMonitor")
foreach ($proc in $killProcs) {
    if (Get-Process -Name $proc -ErrorAction SilentlyContinue) {
        Stop-Process -Name $proc -Force
        Write-Host "Killed: $proc"
    }
}

# 2. Disable services
$svcs = @("AdobeARMservice","AdobeUpdateService","AGSService","AGMService")
foreach ($svc in $svcs) {
    if (Get-Service -Name $svc -ErrorAction SilentlyContinue) {
        Stop-Service -Name $svc -Force
        Set-Service -Name $svc -StartupType Disabled
        Write-Host "Disabled service: $svc"
    }
}

# 3. Remove autorun entries
$runPaths = @(
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"
)
$removeKW = @("Adobe","CCX","CoreSync","AdobeIPC","AcroTray","Creative Cloud","Refresh Manager","AAMUpdater")
foreach ($rp in $runPaths) {
    if (Test-Path $rp) {
        $props = Get-ItemProperty -Path $rp
        foreach ($key in ($props.PSObject.Properties.Name | Where-Object { $_ -notlike "PS*" })) {
            foreach ($kw in $removeKW) {
                if ($key -like "*$kw*") {
                    Remove-ItemProperty -Path $rp -Name $key
                    Write-Host "Removed autorun: $key"
                }
            }
        }
    }
}

# 4. Adobe Refresh Manager registry lockdown
$rmPaths = @(
    "HKLM:\SOFTWARE\Adobe\Adobe Refresh Manager\StartParameters",
    "HKCU:\SOFTWARE\Adobe\Adobe Refresh Manager\StartParameters"
)
foreach ($rmp in $rmPaths) {
    if (-not (Test-Path $rmp)) { New-Item -Path $rmp -Force | Out-Null }
    Set-ItemProperty -Path $rmp -Name "DisableLaunchAtLogin" -Value 1 -Type DWord
    Set-ItemProperty -Path $rmp -Name "disableAutoCheck"     -Value 1 -Type DWord
    Write-Host "Refresh Manager locked: $rmp"
}

# 5. Per-app update policy (bUpdater=0)
$policies = @(
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Photoshop\2023\FeatureLockDown",
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Photoshop\2024\FeatureLockDown",
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Premiere Pro\2023\FeatureLockDown",
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Premiere Pro\2024\FeatureLockDown",
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Illustrator\2022\FeatureLockDown",
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Illustrator\2025\FeatureLockDown",
    "HKLM:\SOFTWARE\Policies\Adobe\After Effects\2020\FeatureLockDown",
    "HKLM:\SOFTWARE\Policies\Adobe\After Effects\2024\FeatureLockDown",
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Acrobat\DC\FeatureLockDown",
    "HKLM:\SOFTWARE\Policies\Adobe\Acrobat Reader\DC\FeatureLockDown",
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Creative Cloud\2.0"
)
foreach ($p in $policies) {
    if (-not (Test-Path $p)) { New-Item -Path $p -Force | Out-Null }
    Set-ItemProperty -Path $p -Name "bUpdater"     -Value 0 -Type DWord
    Set-ItemProperty -Path $p -Name "bCheckReader" -Value 0 -Type DWord
    Write-Host "Policy locked: $(Split-Path $p -Leaf)"
}

# 6. Disable OOBE updater executables
$oobePath = "C:\Program Files (x86)\Common Files\Adobe\OOBE"
if (Test-Path $oobePath) {
    $targets = @("ppmtool.exe","ppml.exe","AdobeRefreshManager.exe","updaternotifications.exe")
    Get-ChildItem -Path $oobePath -Recurse -Filter "*.exe" | Where-Object {
        $targets -contains $_.Name
    } | ForEach-Object {
        $src  = $_.FullName
        $dest = $src + ".disabled"
        if (-not (Test-Path $dest)) {
            Rename-Item -Path $src -NewName ($_.Name + ".disabled") -Force
            Write-Host "Disabled exe: $($_.Name)"
        } else {
            Write-Host "Already disabled: $($_.Name)"
        }
    }
}

# 7. Block update domains in hosts
$hostsPath = "C:\Windows\System32\drivers\etc\hosts"
$domains = @(
    "updates.adobe.com",
    "ardownload.adobe.com",
    "ardownload2.adobe.com",
    "swupmf.adobe.com",
    "swupdl.adobe.com",
    "pdapp.adobe.com",
    "ccmdl.adobe.com",
    "agsupdate.adobe.com",
    "prod.agsupdate.adobe.com",
    "notify.adobe.com",
    "sstats.adobe.com"
)
$hostsContent = Get-Content $hostsPath -Raw
foreach ($domain in $domains) {
    if ($hostsContent -notmatch [regex]::Escape($domain)) {
        Add-Content -Path $hostsPath -Value "127.0.0.1 $domain"
        Write-Host "Hosts blocked: $domain"
    } else {
        Write-Host "Already blocked: $domain"
    }
}

# 8. Firewall: block OOBE update exes (outbound)
if (Test-Path $oobePath) {
    Get-ChildItem -Path $oobePath -Recurse -Filter "*.exe" | Where-Object {
        $_.Name -match "ppm|Refresh|Update|notify"
    } | ForEach-Object {
        $ruleName = "Block Adobe CC Update $($_.Name)"
        Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
        New-NetFirewallRule -DisplayName $ruleName -Direction Outbound -Action Block -Program $_.FullName -Enabled True | Out-Null
        Write-Host "FW blocked: $($_.Name)"
    }
}

# Verify
Write-Host ""
Write-Host "=== DONE ==="
$stillRunning = Get-Process | Where-Object {
    $_.Name -like "*AdobeRefresh*" -or $_.Name -like "*ppmtool*" -or $_.Name -like "*AcroTray*"
}
if ($stillRunning) {
    Write-Host "Still running:" -ForegroundColor Red
    $stillRunning | Select-Object Name, Id | Format-Table
} else {
    Write-Host "No Adobe update processes running. [OK]" -ForegroundColor Green
}
$blockedCount = (Get-Content $hostsPath | Where-Object { $_ -match "127.0.0.1.*adobe" }).Count
Write-Host "Total Adobe domains blocked in hosts: $blockedCount"
Write-Host "Photoshop / Premiere / Illustrator / After Effects: usable normally"
Write-Host "Update popups: BLOCKED"
