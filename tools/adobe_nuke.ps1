# Adobe update/monitoring complete removal script (requires admin)
$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== Adobe Update Removal ===" -ForegroundColor Red

# 1. Delete services
$servicesToDelete = @("AGSService", "AdobeARMservice", "AdobeUpdateService")
foreach ($svc in $servicesToDelete) {
    $exists = Get-Service -Name $svc -ErrorAction SilentlyContinue
    if ($exists) {
        Stop-Service -Name $svc -Force
        $result = (sc.exe delete $svc) 2>&1
        Write-Host "Service deleted: $svc -> $result" -ForegroundColor Yellow
    } else {
        Write-Host "Service not found (skip): $svc" -ForegroundColor Gray
    }
}

# 2. Delete scheduled tasks
$allAdobeTasks = Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object {
    $_.TaskName -like "*Adobe*" -or $_.TaskPath -like "*Adobe*"
}
foreach ($task in $allAdobeTasks) {
    Disable-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Task deleted: $($task.TaskPath)$($task.TaskName)" -ForegroundColor Yellow
}

# 3. Disable CAI helper
$caiPath = "C:\Program Files\Common Files\Adobe\CAI\cai-helper.exe"
if (Test-Path $caiPath) {
    Rename-Item -Path $caiPath -NewName "cai-helper.exe.disabled" -Force
    Write-Host "CAI helper disabled: $caiPath" -ForegroundColor Yellow
} else {
    Write-Host "CAI helper not found (skip)" -ForegroundColor Gray
}

# 4. Registry - disable auto update
$regPaths = @(
    "HKLM:\SOFTWARE\Adobe\Adobe ARM\1.0\ARM",
    "HKLM:\SOFTWARE\WOW6432Node\Adobe\Adobe ARM\1.0\ARM"
)
foreach ($path in $regPaths) {
    if (Test-Path $path) {
        Set-ItemProperty -Path $path -Name "iCheckFileSize" -Value 0 -Type DWord
        Set-ItemProperty -Path $path -Name "iDisableCheckFileSize" -Value 1 -Type DWord
        Write-Host "Registry set: $path" -ForegroundColor Cyan
    }
}

# 5. Kill running Adobe update processes
$adobeProcs = @("AdobeARM", "AGSService", "AGMService", "AdobeGCClient", "AdobeIPCBroker")
foreach ($proc in $adobeProcs) {
    $running = Get-Process -Name $proc -ErrorAction SilentlyContinue
    if ($running) {
        Stop-Process -Name $proc -Force
        Write-Host "Process killed: $proc" -ForegroundColor Red
    }
}

# 6. Final status
Write-Host "`n=== Final Check ===" -ForegroundColor Green
Write-Host "Remaining Adobe services:"
$remainSvc = Get-WmiObject Win32_Service | Where-Object {
    $_.DisplayName -like "*Adobe*" -or $_.Name -like "*AGS*" -or $_.Name -like "*ARM*"
}
if ($remainSvc) {
    $remainSvc | ForEach-Object { Write-Host "  $($_.Name) | $($_.State) | $($_.StartMode)" }
} else {
    Write-Host "  (none) OK" -ForegroundColor Green
}

Write-Host "Remaining Adobe scheduled tasks:"
$remaining = Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -like "*Adobe*" }
if ($remaining) {
    $remaining | ForEach-Object { Write-Host "  $($_.TaskName) | $($_.State)" }
} else {
    Write-Host "  (none) OK" -ForegroundColor Green
}

Write-Host "`nDone. Adobe auto-update/monitoring disabled." -ForegroundColor Green
