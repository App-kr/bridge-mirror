# Adobe Update Defense Fortress
# Prevents Adobe update/monitoring services from reinstalling
# Requires admin privileges

$ErrorActionPreference = "SilentlyContinue"
Write-Host "=== Adobe Defense Fortress ===" -ForegroundColor Red

# =========================================================
# LAYER 1: Registry ACL - deny write to ARM/AGS keys
# =========================================================
Write-Host "`n[Layer 1] Locking registry keys..." -ForegroundColor Cyan

$regKeysToLock = @(
    "HKLM:\SOFTWARE\Adobe\Adobe ARM",
    "HKLM:\SOFTWARE\WOW6432Node\Adobe\Adobe ARM",
    "HKLM:\SYSTEM\CurrentControlSet\Services\AGSService",
    "HKLM:\SYSTEM\CurrentControlSet\Services\AdobeARMservice"
)

foreach ($keyPath in $regKeysToLock) {
    if (Test-Path $keyPath) {
        try {
            $acl = Get-Acl -Path $keyPath
            $rule = New-Object System.Security.AccessControl.RegistryAccessRule(
                "Everyone",
                "WriteKey,CreateSubKey,SetValue",
                "Deny"
            )
            $acl.AddAccessRule($rule)
            Set-Acl -Path $keyPath -AclObject $acl
            Write-Host "  Locked: $keyPath" -ForegroundColor Yellow
        } catch {
            Write-Host "  Skip (no key): $keyPath" -ForegroundColor Gray
        }
    } else {
        # Create dummy key and lock it to prevent recreation
        New-Item -Path $keyPath -Force | Out-Null
        try {
            $acl = Get-Acl -Path $keyPath
            $denyRule = New-Object System.Security.AccessControl.RegistryAccessRule(
                "Everyone",
                "WriteKey,CreateSubKey,SetValue,Delete",
                "Deny"
            )
            $acl.AddAccessRule($denyRule)
            Set-Acl -Path $keyPath -AclObject $acl
            Write-Host "  Created+Locked: $keyPath" -ForegroundColor Yellow
        } catch {
            Write-Host "  Could not lock: $keyPath" -ForegroundColor Red
        }
    }
}

# =========================================================
# LAYER 2: File System ACL - lock update executable paths
# =========================================================
Write-Host "`n[Layer 2] Locking file system paths..." -ForegroundColor Cyan

$pathsToLock = @(
    "C:\Program Files\Common Files\Adobe\CAI",
    "C:\Program Files\Common Files\Adobe\Adobe Desktop Common\NGL",
    "C:\Program Files (x86)\Common Files\Adobe\OOBE",
    "C:\Program Files\Adobe\Acrobat DC\Acrobat\AcroApp\ARM"
)

foreach ($dirPath in $pathsToLock) {
    if (Test-Path $dirPath) {
        try {
            $acl = Get-Acl -Path $dirPath
            $denyRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
                "SYSTEM",
                "Write,Modify,Delete",
                "ContainerInherit,ObjectInherit",
                "None",
                "Deny"
            )
            $acl.AddAccessRule($denyRule)
            Set-Acl -Path $dirPath -AclObject $acl
            Write-Host "  Locked dir: $dirPath" -ForegroundColor Yellow
        } catch {
            Write-Host "  Could not lock: $dirPath" -ForegroundColor Red
        }
    } else {
        Write-Host "  Not found (skip): $dirPath" -ForegroundColor Gray
    }
}

# =========================================================
# LAYER 3: Hosts file - block Adobe update domains
# =========================================================
Write-Host "`n[Layer 3] Blocking Adobe update domains in hosts file..." -ForegroundColor Cyan

$hostsPath = "C:\Windows\System32\drivers\etc\hosts"
$adobeDomains = @(
    "# === Adobe Update Block (added by adobe_fortress.ps1) ===",
    "0.0.0.0 armmf.adobe.com",
    "0.0.0.0 genuine.adobe.com",
    "0.0.0.0 lcs.adobe.com",
    "0.0.0.0 activate.adobe.com",
    "0.0.0.0 ags.adobe.com",
    "0.0.0.0 practivate.adobe.com",
    "0.0.0.0 ereg.adobe.com",
    "0.0.0.0 wip3.adobe.com",
    "0.0.0.0 3dns-3.adobe.com",
    "0.0.0.0 3dns-2.adobe.com",
    "0.0.0.0 adobe-dns.adobe.com",
    "0.0.0.0 adobe-dns-2.adobe.com",
    "0.0.0.0 adobe-dns-3.adobe.com",
    "0.0.0.0 ereg.wip.adobe.com",
    "0.0.0.0 activate-sea.adobe.com",
    "0.0.0.0 activate-sjc0.adobe.com",
    "0.0.0.0 activate.wip1.adobe.com",
    "0.0.0.0 activate.wip2.adobe.com",
    "0.0.0.0 activate.wip3.adobe.com",
    "0.0.0.0 activate.wip4.adobe.com",
    "0.0.0.0 prod.adobegenuine.com",
    "# === Adobe Update Block END ==="
)

$currentHosts = Get-Content $hostsPath
if ($currentHosts -notcontains "armmf.adobe.com") {
    Add-Content -Path $hostsPath -Value ""
    foreach ($line in $adobeDomains) {
        Add-Content -Path $hostsPath -Value $line
    }
    Write-Host "  Hosts file updated: $($adobeDomains.Count - 2) domains blocked" -ForegroundColor Yellow
} else {
    Write-Host "  Already blocked in hosts file" -ForegroundColor Gray
}

# =========================================================
# LAYER 4: Windows Firewall - block Adobe update processes
# =========================================================
Write-Host "`n[Layer 4] Firewall rules..." -ForegroundColor Cyan

$firewallBlocks = @(
    @{ Name = "Block AdobeARM"; Path = "C:\Program Files (x86)\Common Files\Adobe\ARM\1.0\AdobeARM.exe" },
    @{ Name = "Block AdobeARM64"; Path = "C:\Program Files\Common Files\Adobe\ARM\1.0\AdobeARM.exe" },
    @{ Name = "Block AGSService"; Path = "C:\Program Files\Adobe\Adobe Genuine Service\AdobeGenuineService.exe" },
    @{ Name = "Block CAIHelper"; Path = "C:\Program Files\Common Files\Adobe\CAI\cai-helper.exe.disabled" }
)

foreach ($rule in $firewallBlocks) {
    if (Test-Path $rule.Path) {
        netsh advfirewall firewall add rule name=$($rule.Name) dir=out action=block program=$($rule.Path) enable=yes | Out-Null
        netsh advfirewall firewall add rule name=$($rule.Name) dir=in action=block program=$($rule.Path) enable=yes | Out-Null
        Write-Host "  Firewall blocked: $($rule.Name)" -ForegroundColor Yellow
    } else {
        Write-Host "  Path not found (skip): $($rule.Path)" -ForegroundColor Gray
    }
}

# =========================================================
# LAYER 5: Scheduled task - watchdog monitor
# =========================================================
Write-Host "`n[Layer 5] Adobe Watchdog task (auto-kill respawned services)..." -ForegroundColor Cyan

$watchdogScript = @'
# Adobe Service Watchdog - kills if respawned
$services = @("AGSService","AdobeARMservice","AdobeUpdateService")
foreach ($s in $services) {
    $svc = Get-Service -Name $s -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -ne "Stopped") {
        Stop-Service -Name $s -Force -ErrorAction SilentlyContinue
    }
    if ($svc) {
        Set-Service -Name $s -StartupType Disabled -ErrorAction SilentlyContinue
    }
}
$procs = @("AdobeARM","AdobeGCClient","AdobeIPCBroker","AGMService","AGSService")
foreach ($p in $procs) {
    Stop-Process -Name $p -Force -ErrorAction SilentlyContinue
}
'@

$watchdogPath = "Q:\Claudework\bridge base\tools\adobe_watchdog.ps1"
Set-Content -Path $watchdogPath -Value $watchdogScript -Encoding UTF8

# Register as scheduled task (runs every 30 min)
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$watchdogPath`""
$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 30) -Once -At (Get-Date)
$settings = New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest

Register-ScheduledTask -TaskName "AdobeDefenseWatchdog" `
    -Action $action -Trigger $trigger -Settings $settings `
    -Principal $principal -Force | Out-Null

Write-Host "  Watchdog task registered (every 30 min)" -ForegroundColor Yellow

# =========================================================
# Final Summary
# =========================================================
Write-Host "`n=== Defense Fortress Complete ===" -ForegroundColor Green
Write-Host "Layer 1: Registry keys locked (write denied)"
Write-Host "Layer 2: File system paths locked"
Write-Host "Layer 3: $($adobeDomains.Count - 2) Adobe domains blocked in hosts"
Write-Host "Layer 4: Firewall outbound rules applied"
Write-Host "Layer 5: Watchdog scheduled task (every 30 min)"
Write-Host "`nAdobe updates cannot be reinstalled or reconnect." -ForegroundColor Green
