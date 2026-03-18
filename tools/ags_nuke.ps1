$ErrorActionPreference = "SilentlyContinue"
Write-Host "=== Adobe Genuine Software NUKE (Acrobat untouched) ==="

# =========================================================
# 1. Kill all AGS/ARM processes
# =========================================================
Write-Host "`n[1] Killing AGS processes..."
$killList = @(
    "AdobeGCClient",
    "AGCInvokerUtility",
    "AdobeGenuineLauncher",
    "Adobe Genuine Launcher",
    "agshelper",
    "AGSService",
    "HDHelper",
    "armsvc",
    "AdobeARMHelper",
    "AdobeARM"
)
foreach ($proc in $killList) {
    $p = Get-Process -Name $proc -ErrorAction SilentlyContinue
    if ($p) {
        Stop-Process -Name $proc -Force -ErrorAction SilentlyContinue
        Write-Host "  Killed: $proc ($($p.Count) instance(s))"
    }
}

# =========================================================
# 2. Disable AGSService / armsvc
# =========================================================
Write-Host "`n[2] Disabling services..."
$services = @("AGSService", "armsvc", "AdobeARMService")
foreach ($svc in $services) {
    $s = Get-Service $svc -ErrorAction SilentlyContinue
    if ($s) {
        Stop-Service $svc -Force -ErrorAction SilentlyContinue
        Set-Service $svc -StartupType Disabled -ErrorAction SilentlyContinue
        Write-Host "  Disabled: $svc"
    } else {
        Write-Host "  Not found (OK): $svc"
    }
}

# =========================================================
# 3. Rename all AGS executables to .disabled
#    (Acrobat DC\Acrobat 폴더는 절대 건드리지 않음)
# =========================================================
Write-Host "`n[3] Renaming AGS executables to .disabled..."
$gcDir = "C:\Program Files (x86)\Common Files\Adobe\AdobeGCClient"
$armDir = "C:\Program Files (x86)\Common Files\Adobe\ARM\1.0"

$agcExes = @(
    "$gcDir\AdobeGCClient.exe",
    "$gcDir\AGCInvokerUtility.exe",
    "$gcDir\Adobe Genuine Launcher.exe",
    "$gcDir\agshelper.exe",
    "$gcDir\AGSService.exe",
    "$gcDir\HDHelper.exe"
)
$armExes = @(
    "$armDir\armsvc.exe",
    "$armDir\AdobeARMHelper.exe"
    # AdobeARM.exe - 방화벽 이미 차단 / 이름 변경은 추가 보호
    "$armDir\AdobeARM.exe"
)

$allExes = $agcExes + $armExes
foreach ($exe in $allExes) {
    if (Test-Path $exe) {
        # 기존 Deny ACL 제거 후 rename
        $acl = Get-Acl $exe
        $denyRules = $acl.Access | Where-Object { $_.AccessControlType -eq "Deny" }
        foreach ($r in $denyRules) { $acl.RemoveAccessRule($r) | Out-Null }
        Set-Acl -Path $exe -AclObject $acl -ErrorAction SilentlyContinue
        Rename-Item -Path $exe -NewName ([System.IO.Path]::GetFileName($exe) + ".disabled") -Force
        Write-Host "  Renamed: $(Split-Path $exe -Leaf)"
    } elseif (Test-Path ($exe + ".disabled")) {
        Write-Host "  Already disabled: $(Split-Path $exe -Leaf)"
    } else {
        Write-Host "  Not found: $(Split-Path $exe -Leaf)"
    }
}

# =========================================================
# 4. Apply Deny ACL on .disabled files (복원 방지)
# =========================================================
Write-Host "`n[4] Locking .disabled files with Deny ACL..."
foreach ($exe in $allExes) {
    $dis = $exe + ".disabled"
    if (Test-Path $dis) {
        $acl = Get-Acl $dis
        $deny = New-Object System.Security.AccessControl.FileSystemAccessRule(
            "Everyone", "ExecuteFile,Write,Delete,Modify", "None", "None", "Deny"
        )
        $acl.AddAccessRule($deny)
        Set-Acl -Path $dis -AclObject $acl
        Write-Host "  Locked: $(Split-Path $dis -Leaf)"
    }
}

# =========================================================
# 5. Lock AdobeGCClient folder (Everyone Write/Modify/Delete Deny)
# =========================================================
Write-Host "`n[5] Locking AdobeGCClient folder..."
if (Test-Path $gcDir) {
    $acl = Get-Acl $gcDir
    # 기존 deny 제거 후 재적용 (중복 방지)
    $existing = $acl.Access | Where-Object { $_.AccessControlType -eq "Deny" -and $_.IdentityReference -eq "Everyone" }
    foreach ($r in $existing) { $acl.RemoveAccessRule($r) | Out-Null }
    $deny = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "Everyone", "Write,Modify,Delete,CreateFiles,CreateDirectories",
        "ContainerInherit,ObjectInherit", "None", "Deny"
    )
    $acl.AddAccessRule($deny)
    Set-Acl -Path $gcDir -AclObject $acl
    Write-Host "  Locked: $gcDir"
}

# ARM 폴더도 잠금
if (Test-Path $armDir) {
    $acl = Get-Acl $armDir
    $existing = $acl.Access | Where-Object { $_.AccessControlType -eq "Deny" -and $_.IdentityReference -eq "Everyone" }
    foreach ($r in $existing) { $acl.RemoveAccessRule($r) | Out-Null }
    $deny = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "Everyone", "Write,Modify,Delete,CreateFiles,CreateDirectories",
        "ContainerInherit,ObjectInherit", "None", "Deny"
    )
    $acl.AddAccessRule($deny)
    Set-Acl -Path $armDir -AclObject $acl
    Write-Host "  Locked: $armDir"
}

# =========================================================
# 6. Firewall rules for ALL AGS executables (원래 경로 기준)
# =========================================================
Write-Host "`n[6] Adding firewall rules..."
$fwRules = @(
    @{ Name="Block AdobeGCClient";          Path="$gcDir\AdobeGCClient.exe" },
    @{ Name="Block AGCInvokerUtility";      Path="$gcDir\AGCInvokerUtility.exe" },
    @{ Name="Block AdobeGenuineLauncher";   Path="$gcDir\Adobe Genuine Launcher.exe" },
    @{ Name="Block agshelper";              Path="$gcDir\agshelper.exe" },
    @{ Name="Block AGSService";             Path="$gcDir\AGSService.exe" },
    @{ Name="Block HDHelper";               Path="$gcDir\HDHelper.exe" },
    @{ Name="Block armsvc";                 Path="$armDir\armsvc.exe" },
    @{ Name="Block AdobeARMHelper";         Path="$armDir\AdobeARMHelper.exe" }
)
foreach ($r in $fwRules) {
    Remove-NetFirewallRule -DisplayName $r.Name -ErrorAction SilentlyContinue
    Remove-NetFirewallRule -DisplayName "$($r.Name) IN" -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName $r.Name -Direction Outbound -Action Block -Program $r.Path -Enabled True | Out-Null
    New-NetFirewallRule -DisplayName "$($r.Name) IN" -Direction Inbound -Action Block -Program $r.Path -Enabled True | Out-Null
    Write-Host "  Blocked: $($r.Name)"
}

# =========================================================
# 7. Registry — Disable AGS update triggers
#    (HKLM\SOFTWARE\Adobe\Adobe Genuine Service)
# =========================================================
Write-Host "`n[7] Registry lockdown..."
$regPaths = @(
    "HKLM:\SOFTWARE\Adobe\Adobe Genuine Service",
    "HKLM:\SOFTWARE\WOW6432Node\Adobe\Adobe Genuine Service",
    "HKLM:\SOFTWARE\Adobe\Adobe GCClient",
    "HKLM:\SOFTWARE\WOW6432Node\Adobe\Adobe GCClient"
)
foreach ($rp in $regPaths) {
    if (Test-Path $rp) {
        # iDisable 플래그 설정
        Set-ItemProperty -Path $rp -Name "iDisableAGSCheck" -Value 1 -Type DWord -ErrorAction SilentlyContinue
        Set-ItemProperty -Path $rp -Name "bUpdater" -Value 0 -Type DWord -ErrorAction SilentlyContinue

        # 레지스트리 키 ACL 잠금 (Everyone WriteKey Deny)
        try {
            $regKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey(
                $rp.Replace("HKLM:\", ""), [Microsoft.Win32.RegistryKeyPermissionCheck]::ReadWriteSubTree,
                [System.Security.AccessControl.RegistryRights]::ChangePermissions
            )
            if ($regKey) {
                $regAcl = $regKey.GetAccessControl()
                $denyRule = New-Object System.Security.AccessControl.RegistryAccessRule(
                    "Everyone",
                    [System.Security.AccessControl.RegistryRights]::WriteKey,
                    [System.Security.AccessControl.InheritanceFlags]::ContainerInherit,
                    [System.Security.AccessControl.PropagationFlags]::None,
                    [System.Security.AccessControl.AccessControlType]::Deny
                )
                $regAcl.AddAccessRule($denyRule)
                $regKey.SetAccessControl($regAcl)
                $regKey.Close()
                Write-Host "  Registry locked: $rp"
            }
        } catch {
            Write-Host "  Registry ACL skipped (no perms): $rp"
        }
    }
}

# AGS 관련 예약 작업 삭제 (Watchdog 제외)
Write-Host "`n[8] Removing AGS scheduled tasks..."
$taskNames = @(
    "Adobe Acrobat Update Task",
    "Adobe Flash Player Updater",
    "AdobeGCInvoker-1.0",
    "AdobeGCInvoker*"
)
foreach ($t in $taskNames) {
    $task = Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
    if ($task) {
        Unregister-ScheduledTask -TaskName $t -Confirm:$false
        Write-Host "  Removed task: $t"
    }
}

# =========================================================
# 9. Hosts file — block AGS domains
# =========================================================
Write-Host "`n[9] Blocking AGS domains in hosts file..."
$hostsPath = "C:\Windows\System32\drivers\etc\hosts"
$blockedDomains = @(
    "genuine.adobe.com",
    "lcs-cops.adobe.io",
    "lcs-ulecs.adobe.io",
    "prod.agsupdate.adobe.com",
    "gc.cloud.adobe.io",
    "genuineservice.adobe.com",
    "genuinecheck.adobe.com"
)
$hostsContent = Get-Content $hostsPath -Raw
$changed = $false
foreach ($domain in $blockedDomains) {
    if ($hostsContent -notmatch [regex]::Escape($domain)) {
        Add-Content -Path $hostsPath -Value "127.0.0.1 $domain"
        $changed = $true
        Write-Host "  Blocked: $domain"
    } else {
        Write-Host "  Already blocked: $domain"
    }
}

# =========================================================
# 10. Verification
# =========================================================
Write-Host "`n=== VERIFICATION ==="

Write-Host "`nProcesses (should be 0):"
$remaining = Get-Process | Where-Object {
    $_.Name -like "*AdobeGC*" -or $_.Name -like "*AGCInvoker*" -or
    $_.Name -like "*AGSService*" -or $_.Name -like "*agshelper*" -or
    $_.Name -like "*armsvc*" -or $_.Name -like "*AdobeARMHelper*"
}
if ($remaining) {
    $remaining | Select-Object Name, Id | Format-Table -AutoSize
} else {
    Write-Host "  [OK] No AGS processes running"
}

Write-Host "`nFile status:"
foreach ($exe in $allExes) {
    $exeExists = Test-Path $exe
    $disExists = Test-Path ($exe + ".disabled")
    if ($disExists -and -not $exeExists) {
        Write-Host "  [OK DISABLED] $(Split-Path $exe -Leaf)" -ForegroundColor Green
    } elseif ($exeExists) {
        Write-Host "  [STILL EXISTS] $(Split-Path $exe -Leaf)" -ForegroundColor Red
    } else {
        Write-Host "  [NOT FOUND] $(Split-Path $exe -Leaf)" -ForegroundColor Yellow
    }
}

Write-Host "`nFirewall rules (AGS):"
Get-NetFirewallRule | Where-Object {
    $_.DisplayName -like "*AdobeGC*" -or $_.DisplayName -like "*AGCInvoker*" -or
    $_.DisplayName -like "*AGSService*" -or $_.DisplayName -like "*armsvc*" -or
    $_.DisplayName -like "*HDHelper*" -or $_.DisplayName -like "*agshelper*" -or
    $_.DisplayName -like "*AdobeARMHelper*" -or $_.DisplayName -like "*GenuineLauncher*"
} | Select-Object DisplayName, Direction, Action | Format-Table -AutoSize

Write-Host "`nDone. Adobe Genuine fully blocked. Acrobat Reader untouched." -ForegroundColor Green
