$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== ACTUAL STATE VERIFICATION ==="

# 1. 파일 실제 존재 여부
Write-Host "`n[1] File Status:"
$files = @(
    "C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\AdobeCollabSync.exe",
    "C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\AdobeCollabSync.exe.disabled",
    "C:\Program Files (x86)\Common Files\Adobe\Adobe Desktop Common\IPCBox\AdobeIPCBroker.exe",
    "C:\Program Files (x86)\Common Files\Adobe\Adobe Desktop Common\IPCBox\AdobeIPCBroker.exe.disabled",
    "C:\Program Files\Common Files\Adobe\Creative Cloud Libraries\CCLibrary.exe",
    "C:\Program Files\Common Files\Adobe\Creative Cloud Libraries\CCLibrary.exe.disabled",
    "C:\Program Files (x86)\Common Files\Adobe\OOBE\PDApp\UWA\UpdaterStartupUtility.exe",
    "C:\Program Files (x86)\Common Files\Adobe\OOBE\PDApp\UWA\UpdaterStartupUtility.exe.disabled"
)
foreach ($f in $files) {
    if (Test-Path $f) {
        Write-Host "  EXISTS: $f" -ForegroundColor $(if ($f -like "*.disabled") {"Green"} else {"Red"})
    }
}

# 2. 현재 실행 중인 프로세스
Write-Host "`n[2] Running Adobe Processes:"
$procs = Get-Process | Where-Object {
    $_.Name -like "*Collab*" -or $_.Name -like "*IPC*" -or
    $_.Name -like "*AdobeGC*" -or $_.Name -like "*CCLib*" -or
    $_.Name -like "*Adobe*"
}
if ($procs) {
    $procs | Select-Object Name, Id, Path | Format-Table -AutoSize
} else {
    Write-Host "  None" -ForegroundColor Green
}

# 3. 방화벽 룰 실제 확인
Write-Host "`n[3] Firewall Rules (Adobe related):"
netsh advfirewall firewall show rule name=all dir=out verbose 2>&1 | Select-String -Pattern "AdobeCollabSync|IPCBroker|AdobeARM|Block Adobe|Block Acrobat" | ForEach-Object { Write-Host "  $_" }

# 4. 레지스트리 실제 값
Write-Host "`n[4] Registry bUpdater values:"
$regPaths = @(
    "HKCU:\SOFTWARE\Adobe\Adobe Acrobat\DC\Updater",
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Acrobat\DC\FeatureLockDown"
)
foreach ($p in $regPaths) {
    if (Test-Path $p) {
        $val = Get-ItemProperty $p -ErrorAction SilentlyContinue
        Write-Host "  $p"
        $val.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" } | ForEach-Object {
            Write-Host "    $($_.Name) = $($_.Value)"
        }
    } else {
        Write-Host "  NOT FOUND: $p" -ForegroundColor Red
    }
}

# 5. 예약 작업
Write-Host "`n[5] Scheduled Tasks (Adobe):"
Get-ScheduledTask | Where-Object { $_.TaskName -like "*Adobe*" -or $_.TaskName -like "*Watchdog*" } | Select-Object TaskName, State | Format-Table -AutoSize

# 6. Autorun 레지스트리 전체 (Adobe 관련)
Write-Host "`n[6] All AutoRun entries (Adobe):"
$runPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"
)
$found = $false
foreach ($path in $runPaths) {
    if (Test-Path $path) {
        $props = Get-ItemProperty $path -ErrorAction SilentlyContinue
        $props.PSObject.Properties | Where-Object {
            $_.Name -notlike "PS*" -and ($_.Value -like "*adobe*" -or $_.Value -like "*acro*" -or $_.Value -like "*collab*")
        } | ForEach-Object {
            Write-Host "  [$path] $($_.Name) = $($_.Value)" -ForegroundColor Red
            $found = $true
        }
    }
}
if (-not $found) { Write-Host "  None found" -ForegroundColor Green }
