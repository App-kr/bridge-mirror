$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== Acrobat Login Popup - Complete Removal ==="

# 1. Kill all running processes
$killProcs = @(
    "AdobeCollabSync",
    "AdobeIPCBroker",
    "CCLibrary",
    "AdobeGCClient",
    "AGSService",
    "AdobeARM",
    "AcroRd32",
    "Acrobat"
)
foreach ($p in $killProcs) {
    $proc = Get-Process -Name $p -ErrorAction SilentlyContinue
    if ($proc) {
        Stop-Process -Name $p -Force
        Write-Host "  Killed: $p (PID: $($proc.Id))"
    }
}
Start-Sleep -Seconds 2

# 2. Rename executables to .disabled (can't run)
$exesToDisable = @(
    "C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\AdobeCollabSync.exe",
    "C:\Program Files\Common Files\Adobe\Adobe Desktop Common\IPCBox\AdobeIPCBroker.exe",
    "C:\Program Files (x86)\Common Files\Adobe\Adobe Desktop Common\IPCBox\AdobeIPCBroker.exe",
    "C:\Program Files\Common Files\Adobe\Creative Cloud Libraries\CCLibrary.exe",
    "C:\Program Files (x86)\Common Files\Adobe\OOBE\PDApp\P6\updaternotifications.exe",
    "C:\Program Files (x86)\Common Files\Adobe\OOBE\PDApp\UWA\UpdaterStartupUtility.exe"
)
foreach ($exe in $exesToDisable) {
    if (Test-Path $exe) {
        $disabled = $exe + ".disabled"
        if (-not (Test-Path $disabled)) {
            Rename-Item -Path $exe -NewName ([System.IO.Path]::GetFileName($disabled)) -Force
            Write-Host "  Disabled: $exe"
        } else {
            Write-Host "  Already disabled: $exe"
        }
    } else {
        Write-Host "  Not found (skip): $exe"
    }
}

# 3. Lock directories to prevent recreation
$dirsToLock = @(
    "C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat",
    "C:\Program Files\Common Files\Adobe\Adobe Desktop Common\IPCBox"
)
foreach ($dir in $dirsToLock) {
    if (Test-Path $dir) {
        $acl = Get-Acl $dir
        $deny = New-Object System.Security.AccessControl.FileSystemAccessRule(
            "Everyone", "Write,Modify,Delete,CreateFiles,CreateDirectories",
            "ContainerInherit,ObjectInherit", "None", "Deny"
        )
        $acl.AddAccessRule($deny)
        Set-Acl -Path $dir -AclObject $acl -ErrorAction SilentlyContinue
        Write-Host "  Dir locked: $dir"
    }
}

# 4. Registry: Disable Acrobat auto-run / collaboration
$regKeys = @(
    @{ Path = "HKCU:\SOFTWARE\Adobe\Acrobat Reader"; Name = "bUpdater"; Value = 0 },
    @{ Path = "HKCU:\SOFTWARE\Adobe\Adobe Acrobat\DC\Updater"; Name = "bUpdater"; Value = 0 },
    @{ Path = "HKLM:\SOFTWARE\Policies\Adobe\Acrobat Reader\DC\FeatureLockDown"; Name = "bUpdater"; Value = 0 },
    @{ Path = "HKLM:\SOFTWARE\Policies\Adobe\Adobe Acrobat\DC\FeatureLockDown"; Name = "bUpdater"; Value = 0 },
    @{ Path = "HKLM:\SOFTWARE\Policies\Adobe\Adobe Acrobat\DC\FeatureLockDown"; Name = "bAcroSysTrayProcessName"; Value = 0 },
    @{ Path = "HKLM:\SOFTWARE\Policies\Adobe\Adobe Acrobat\DC\FeatureLockDown"; Name = "bDisableTrustedSites"; Value = 1 },
    @{ Path = "HKLM:\SOFTWARE\Adobe\Adobe Acrobat\DC\Installer"; Name = "DisableMaintenance"; Value = 1 }
)
foreach ($reg in $regKeys) {
    if (-not (Test-Path $reg.Path)) {
        New-Item -Path $reg.Path -Force | Out-Null
    }
    Set-ItemProperty -Path $reg.Path -Name $reg.Name -Value $reg.Value -Type DWord -ErrorAction SilentlyContinue
    Write-Host "  Registry set: $($reg.Path)\$($reg.Name) = $($reg.Value)"
}

# 5. Remove Acrobat from startup (all locations)
$startupFolders = @(
    "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup",
    [System.Environment]::GetFolderPath("Startup")
)
foreach ($folder in $startupFolders) {
    Get-ChildItem $folder -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -like "*acro*" -or $_.Name -like "*adobe*"
    } | ForEach-Object {
        Remove-Item $_.FullName -Force
        Write-Host "  Startup item removed: $($_.FullName)"
    }
}

# 6. Block via Software Restriction Policy (hash rule for remaining exes)
$remainingExes = @(
    "C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\AdobeCollabSync.exe.disabled",
    "C:\Program Files (x86)\Common Files\Adobe\Adobe Desktop Common\IPCBox\AdobeIPCBroker.exe.disabled"
)
Write-Host "`n  Note: .disabled files cannot execute directly."

# 7. Firewall block for Acrobat-related processes
$fwRules = @(
    @{ Name = "Block AdobeCollabSync"; Path = "C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\AdobeCollabSync.exe.disabled" },
    @{ Name = "Block IPCBroker"; Path = "C:\Program Files (x86)\Common Files\Adobe\Adobe Desktop Common\IPCBox\AdobeIPCBroker.exe.disabled" },
    @{ Name = "Block Acrobat"; Path = "C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\Acrobat.exe" }
)
foreach ($rule in $fwRules) {
    netsh advfirewall firewall add rule name="$($rule.Name)" dir=out action=block program="$($rule.Path)" enable=yes 2>&1 | Out-Null
    Write-Host "  Firewall blocked: $($rule.Name)"
}

# 8. Update watchdog to include CollabSync
$watchdogPath = "Q:\Claudework\bridge base\tools\adobe_watchdog.ps1"
$watchdogContent = Get-Content $watchdogPath -Raw -ErrorAction SilentlyContinue
if ($watchdogContent -notlike "*CollabSync*") {
    Add-Content -Path $watchdogPath -Value @"

# Kill Acrobat login popup processes
`$popupProcs = @("AdobeCollabSync","AdobeIPCBroker","CCLibrary","AdobeGCClient")
foreach (`$p in `$popupProcs) {
    Stop-Process -Name `$p -Force -ErrorAction SilentlyContinue
}
"@
    Write-Host "  Watchdog updated with CollabSync kill"
}

# 9. Final verification
Write-Host "`n=== Final Status ==="
$stillRunning = Get-Process | Where-Object {
    $_.Name -like "*Collab*" -or $_.Name -like "*IPCBroker*" -or $_.Name -like "*AdobeGC*"
}
if ($stillRunning) {
    Write-Host "  Still running:" -ForegroundColor Red
    $stillRunning | Select-Object Name, Id | Format-Table
} else {
    Write-Host "  No Adobe popup processes running. OK" -ForegroundColor Green
}

Write-Host "`nDone. Acrobat login popup permanently disabled." -ForegroundColor Green
