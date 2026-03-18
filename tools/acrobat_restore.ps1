$ErrorActionPreference = "SilentlyContinue"
Write-Host "=== Acrobat Reader Restore (keep popup blocked) ==="

# =========================================================
# 1. Acrobat 폴더 ACL 잠금 해제 (실행 깨짐 원인)
# =========================================================
Write-Host "`n[1] Removing directory lock on Acrobat folders..."
$lockedDirs = @(
    "C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat",
    "C:\Program Files\Common Files\Adobe\Adobe Desktop Common\NGL",
    "C:\Program Files (x86)\Common Files\Adobe\OOBE",
    "C:\Program Files\Common Files\Adobe\CAI"
)
foreach ($dir in $lockedDirs) {
    if (Test-Path $dir) {
        $acl = Get-Acl $dir
        $changed = $false
        $rulesToRemove = $acl.Access | Where-Object {
            $_.AccessControlType -eq "Deny" -and
            ($_.IdentityReference -eq "Everyone" -or $_.IdentityReference -eq "NT AUTHORITY\SYSTEM")
        }
        foreach ($rule in $rulesToRemove) {
            $acl.RemoveAccessRule($rule) | Out-Null
            $changed = $true
        }
        if ($changed) {
            Set-Acl -Path $dir -AclObject $acl
            Write-Host "  Unlocked: $dir"
        } else {
            Write-Host "  No deny rules found: $dir"
        }
    }
}

# =========================================================
# 2. AdobeIPCBroker 복원 (Acrobat 필수 프로세스)
# =========================================================
Write-Host "`n[2] Restoring AdobeIPCBroker.exe (required for Acrobat)..."
$ipcDisabled = "C:\Program Files (x86)\Common Files\Adobe\Adobe Desktop Common\IPCBox\AdobeIPCBroker.exe.disabled"
$ipcOriginal = "C:\Program Files (x86)\Common Files\Adobe\Adobe Desktop Common\IPCBox\AdobeIPCBroker.exe"
if (Test-Path $ipcDisabled) {
    # 파일 자체의 Deny ACL 먼저 제거
    $acl = Get-Acl $ipcDisabled
    $denyRules = $acl.Access | Where-Object { $_.AccessControlType -eq "Deny" }
    foreach ($r in $denyRules) { $acl.RemoveAccessRule($r) | Out-Null }
    Set-Acl -Path $ipcDisabled -AclObject $acl
    Rename-Item -Path $ipcDisabled -NewName "AdobeIPCBroker.exe" -Force
    Write-Host "  Restored: AdobeIPCBroker.exe"
} elseif (Test-Path $ipcOriginal) {
    Write-Host "  Already exists: AdobeIPCBroker.exe"
} else {
    Write-Host "  NOT FOUND: $ipcDisabled" -ForegroundColor Red
}

# IPCBroker 방화벽 차단 제거 (로컬 IPC 필요)
Remove-NetFirewallRule -DisplayName "Block AdobeIPCBroker" -ErrorAction SilentlyContinue
Remove-NetFirewallRule -DisplayName "Block AdobeIPCBroker IN" -ErrorAction SilentlyContinue
Write-Host "  Firewall block removed for IPCBroker"

# IPCBroker의 Deny ACL도 제거 (이미 복원 시 처리했지만 확인)
if (Test-Path $ipcOriginal) {
    $acl = Get-Acl $ipcOriginal
    $denyRules = $acl.Access | Where-Object { $_.AccessControlType -eq "Deny" }
    if ($denyRules) {
        foreach ($r in $denyRules) { $acl.RemoveAccessRule($r) | Out-Null }
        Set-Acl -Path $ipcOriginal -AclObject $acl
        Write-Host "  Deny ACL cleared on AdobeIPCBroker.exe"
    }
}

# =========================================================
# 3. CCLibrary 복원 (일부 Acrobat DC 기능에 필요)
# =========================================================
Write-Host "`n[3] Restoring CCLibrary.exe..."
$ccDisabled = "C:\Program Files\Common Files\Adobe\Creative Cloud Libraries\CCLibrary.exe.disabled"
$ccOriginal = "C:\Program Files\Common Files\Adobe\Creative Cloud Libraries\CCLibrary.exe"
if (Test-Path $ccDisabled) {
    $acl = Get-Acl $ccDisabled
    $denyRules = $acl.Access | Where-Object { $_.AccessControlType -eq "Deny" }
    foreach ($r in $denyRules) { $acl.RemoveAccessRule($r) | Out-Null }
    Set-Acl -Path $ccDisabled -AclObject $acl
    Rename-Item -Path $ccDisabled -NewName "CCLibrary.exe" -Force
    Write-Host "  Restored: CCLibrary.exe"
} else {
    Write-Host "  Already exists or not found"
}
Remove-NetFirewallRule -DisplayName "Block CCLibrary" -ErrorAction SilentlyContinue
Remove-NetFirewallRule -DisplayName "Block CCLibrary IN" -ErrorAction SilentlyContinue
Write-Host "  Firewall block removed for CCLibrary"

# =========================================================
# 4. AdobeCollabSync 는 유지 (로그인 팝업 원인 — 복원 안 함)
# =========================================================
Write-Host "`n[4] AdobeCollabSync stays DISABLED (login popup source)"
Write-Host "  File: AdobeCollabSync.exe.disabled - KEPT"
Write-Host "  Firewall: Block AdobeCollabSync - KEPT"

# CollabSync Deny ACL 유지 확인
$collabDisabled = "C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\AdobeCollabSync.exe.disabled"
if (Test-Path $collabDisabled) {
    $acl = Get-Acl $collabDisabled
    $hasDeny = $acl.Access | Where-Object { $_.AccessControlType -eq "Deny" }
    if (-not $hasDeny) {
        $deny = New-Object System.Security.AccessControl.FileSystemAccessRule(
            "Everyone", "ExecuteFile,Write,Delete,Modify", "None", "None", "Deny"
        )
        $acl.AddAccessRule($deny)
        Set-Acl -Path $collabDisabled -AclObject $acl
        Write-Host "  CollabSync Deny ACL re-applied"
    } else {
        Write-Host "  CollabSync Deny ACL already in place"
    }
}

# =========================================================
# 5. 최종 검증
# =========================================================
Write-Host "`n=== Verification ==="

Write-Host "`nFile status:"
$checkFiles = @(
    "C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\AdobeCollabSync.exe",
    "C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\AdobeCollabSync.exe.disabled",
    "C:\Program Files (x86)\Common Files\Adobe\Adobe Desktop Common\IPCBox\AdobeIPCBroker.exe",
    "C:\Program Files\Common Files\Adobe\Creative Cloud Libraries\CCLibrary.exe"
)
foreach ($f in $checkFiles) {
    $exists = Test-Path $f
    $status = if ($exists) { "EXISTS" } else { "MISSING" }
    $color = if ($f -like "*CollabSync.exe" -and $exists) { "Red" }
             elseif ($f -like "*CollabSync.exe.disabled" -and $exists) { "Green" }
             elseif ($exists) { "Green" }
             else { "Yellow" }
    Write-Host "  [$status] $([System.IO.Path]::GetFileName($f))" -ForegroundColor $color
}

Write-Host "`nFirewall rules (CollabSync block must exist):"
Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*AdobeCollabSync*" } | ForEach-Object {
    $filter = $_ | Get-NetFirewallApplicationFilter
    Write-Host "  $($_.DisplayName) | $($_.Direction) | $($_.Action)"
}

Write-Host "`nDone. Acrobat Reader should work. Login popup remains blocked." -ForegroundColor Green
