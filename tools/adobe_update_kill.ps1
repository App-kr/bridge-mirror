# Adobe Acrobat Update Complete Blocker

Write-Host "=== Step 1: Kill processes ==="
$procs = @('AdobeARM','AdobeARMHelper','AcrobatUpdater','AdobeUpdateService','AdobeNotificationClient','AdobeGCClient')
foreach ($p in $procs) {
    $found = Get-Process -Name $p -ErrorAction SilentlyContinue
    if ($found) {
        $found | Stop-Process -Force
        Write-Host "Killed: $p"
    }
}

Write-Host "=== Step 2: Disable service ==="
$svc = Get-Service -Name 'AdobeARMservice' -ErrorAction SilentlyContinue
if ($svc) {
    Stop-Service 'AdobeARMservice' -Force -ErrorAction SilentlyContinue
    Set-Service 'AdobeARMservice' -StartupType Disabled
    Write-Host "Service disabled: AdobeARMservice"
} else {
    Write-Host "Service not found: AdobeARMservice"
}

Write-Host "=== Step 3: Disable ALL Adobe scheduled tasks ==="
$tasks = Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object {
    $_.TaskName -like '*Adobe*' -or $_.TaskName -like '*Acrobat*'
}
foreach ($t in $tasks) {
    Disable-ScheduledTask -TaskName $t.TaskName -TaskPath $t.TaskPath -ErrorAction SilentlyContinue | Out-Null
    Write-Host "Task disabled: $($t.TaskName)"
}

Write-Host "=== Step 4: Registry - disable updater ==="
$policyPath = "HKLM:\SOFTWARE\Policies\Adobe\Adobe Acrobat\DC\FeatureLockDown"
if (-not (Test-Path $policyPath)) { New-Item -Path $policyPath -Force | Out-Null }
Set-ItemProperty -Path $policyPath -Name "bUpdater" -Value 0 -Type DWord -ErrorAction SilentlyContinue
Write-Host "Registry: Acrobat DC bUpdater=0"

$policyPathReader = "HKLM:\SOFTWARE\Policies\Adobe\Acrobat Reader\DC\FeatureLockDown"
if (-not (Test-Path $policyPathReader)) { New-Item -Path $policyPathReader -Force | Out-Null }
Set-ItemProperty -Path $policyPathReader -Name "bUpdater" -Value 0 -Type DWord -ErrorAction SilentlyContinue
Write-Host "Registry: Reader DC bUpdater=0"

Write-Host "=== Step 5: Find and block AdobeARM.exe ==="
$searchPaths = @("C:\Program Files","C:\Program Files (x86)","D:\Program Files","D:\Program Files (x86)")
foreach ($sp in $searchPaths) {
    if (Test-Path $sp) {
        $armFiles = Get-ChildItem -Path $sp -Recurse -Filter "AdobeARM.exe" -ErrorAction SilentlyContinue
        foreach ($f in $armFiles) {
            Write-Host "Found: $($f.FullName)"
            try {
                $acl = Get-Acl $f.FullName
                $acl.SetAccessRuleProtection($true, $false)
                $deny = New-Object System.Security.AccessControl.FileSystemAccessRule("Everyone","ExecuteFile","Deny")
                $acl.AddAccessRule($deny)
                Set-Acl -Path $f.FullName -AclObject $acl -ErrorAction Stop
                Write-Host "Execution BLOCKED: $($f.FullName)"
            } catch {
                Write-Host "Could not block (need TrustedInstaller): $($f.FullName)"
            }
        }
    }
}

Write-Host ""
Write-Host "DONE - Adobe update popups blocked."
