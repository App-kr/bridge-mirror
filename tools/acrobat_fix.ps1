$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== Fix: Correct Firewall Rules + NTFS Execute Deny ==="

# =========================================================
# 1. 잘못된 방화벽 룰 삭제 (.disabled 경로 → 무의미)
# =========================================================
Write-Host "`n[1] Removing wrong firewall rules (.disabled paths)..."
$wrongRules = @("Block AdobeCollabSync", "Block IPCBroker", "Block Acrobat", "Block CAIHelper", "Block AdobeARM")
foreach ($r in $wrongRules) {
    netsh advfirewall firewall delete rule name="$r" 2>&1 | Out-Null
    Write-Host "  Deleted rule: $r"
}

# =========================================================
# 2. 올바른 방화벽 룰 추가 (원본 .exe 경로로 차단)
# =========================================================
Write-Host "`n[2] Adding correct firewall rules (original .exe paths)..."

$fwTargets = @(
    @{ Name = "Block AdobeCollabSync"; Path = "C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\AdobeCollabSync.exe" },
    @{ Name = "Block AdobeIPCBroker"; Path = "C:\Program Files (x86)\Common Files\Adobe\Adobe Desktop Common\IPCBox\AdobeIPCBroker.exe" },
    @{ Name = "Block CCLibrary"; Path = "C:\Program Files\Common Files\Adobe\Creative Cloud Libraries\CCLibrary.exe" },
    @{ Name = "Block AdobeARM"; Path = "C:\Program Files (x86)\Common Files\Adobe\ARM\1.0\AdobeARM.exe" },
    @{ Name = "Block CAIHelper"; Path = "C:\Program Files\Common Files\Adobe\CAI\cai-helper.exe" },
    @{ Name = "Block AdobeUpdater"; Path = "C:\Program Files (x86)\Common Files\Adobe\OOBE\PDApp\UWA\UpdaterStartupUtility.exe" }
)

foreach ($rule in $fwTargets) {
    # 경로 실제 존재 여부와 무관하게 등록 (파일 복원 시 즉시 차단됨)
    $r1 = netsh advfirewall firewall add rule name="$($rule.Name)" dir=out action=block program="$($rule.Path)" enable=yes 2>&1
    $r2 = netsh advfirewall firewall add rule name="$($rule.Name) IN" dir=in action=block program="$($rule.Path)" enable=yes 2>&1
    Write-Host "  Rule added: $($rule.Name) -> $($rule.Path)"
}

# =========================================================
# 3. NTFS: 원본 .exe 경로에 Everyone Execute Deny 설정
#    (파일이 복원되어도 실행 불가)
# =========================================================
Write-Host "`n[3] Setting NTFS Deny Execute on .exe paths..."

$execPaths = @(
    "C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\AdobeCollabSync.exe.disabled",
    "C:\Program Files (x86)\Common Files\Adobe\Adobe Desktop Common\IPCBox\AdobeIPCBroker.exe.disabled",
    "C:\Program Files\Common Files\Adobe\Creative Cloud Libraries\CCLibrary.exe.disabled",
    "C:\Program Files (x86)\Common Files\Adobe\OOBE\PDApp\UWA\UpdaterStartupUtility.exe.disabled"
)

foreach ($filePath in $execPaths) {
    if (Test-Path $filePath) {
        $acl = Get-Acl -Path $filePath
        # Deny Execute + Write + Delete for Everyone
        $denyExec = New-Object System.Security.AccessControl.FileSystemAccessRule(
            "Everyone",
            "ExecuteFile,Write,Delete,Modify",
            "None", "None", "Deny"
        )
        $acl.AddAccessRule($denyExec)
        Set-Acl -Path $filePath -AclObject $acl
        Write-Host "  NTFS Deny Execute+Write set: $filePath"
    } else {
        Write-Host "  Not found: $filePath"
    }
}

# =========================================================
# 4. 검증: 방화벽 룰 실제 확인
# =========================================================
Write-Host "`n[4] Verification - Active firewall rules:"
$check = netsh advfirewall firewall show rule name=all dir=out verbose 2>&1
$lines = $check -split "`n"
$capture = $false
$ruleName = ""
foreach ($line in $lines) {
    if ($line -match "Rule Name:" -and ($line -match "Block Adobe|Block IPC|Block CC|Block ARM|Block CAI")) {
        $capture = $true
        $ruleName = $line.Trim()
    }
    if ($capture -and $line -match "Program:") {
        Write-Host "  $ruleName"
        Write-Host "    $($line.Trim())"
        $capture = $false
    }
}

# =========================================================
# 5. 검증: NTFS ACL 확인
# =========================================================
Write-Host "`n[5] Verification - NTFS ACL on key files:"
foreach ($filePath in $execPaths) {
    if (Test-Path $filePath) {
        $acl = Get-Acl -Path $filePath
        $denyRules = $acl.Access | Where-Object { $_.AccessControlType -eq "Deny" }
        if ($denyRules) {
            Write-Host "  OK - Deny rules set: $([System.IO.Path]::GetFileName($filePath))"
            $denyRules | ForEach-Object { Write-Host "       $($_.IdentityReference): $($_.FileSystemRights)" }
        } else {
            Write-Host "  WARN - No deny rules: $filePath" -ForegroundColor Red
        }
    }
}

Write-Host "`n=== Fix Complete ===" -ForegroundColor Green
