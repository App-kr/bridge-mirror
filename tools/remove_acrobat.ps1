# Acrobat / Adobe 관련 전체 삭제 스크립트

$targets = @(
    "C:\Program Files\Adobe",
    "C:\Program Files (x86)\Adobe",
    "C:\ProgramData\Adobe",
    "$env:LOCALAPPDATA\Adobe",
    "$env:APPDATA\Adobe",
    "$env:USERPROFILE\AppData\LocalLow\Adobe"
)

Write-Host "=== Scan ==="
foreach ($path in $targets) {
    if (Test-Path $path) {
        $sz = (Get-ChildItem $path -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        $mb = [math]::Round($sz / 1MB, 0)
        Write-Host "FOUND  ${mb}MB  $path"
    } else {
        Write-Host "SKIP           $path"
    }
}

# Acrobat 관련 예약작업 확인
Write-Host "`n=== Scheduled Tasks ==="
Get-ScheduledTask | Where-Object { $_.TaskName -match "Adobe|Acrobat" } | ForEach-Object {
    Write-Host "TASK: $($_.TaskPath)$($_.TaskName)"
}

# Acrobat 관련 서비스 확인
Write-Host "`n=== Services ==="
Get-Service | Where-Object { $_.Name -match "Adobe|Acrobat" } -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "SERVICE: $($_.Name) [$($_.Status)]"
}

Write-Host "`n=== Deleting ==="
foreach ($path in $targets) {
    if (Test-Path $path) {
        Write-Host "Taking ownership: $path"
        & takeown /F $path /R /D Y 2>&1 | Out-Null
        & icacls $path /grant "$($env:USERNAME):F" /T /C /Q 2>&1 | Out-Null
        Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
        if (Test-Path $path) {
            Write-Host "FAILED: $path"
        } else {
            Write-Host "DELETED: $path"
        }
    }
}

# 예약작업 삭제
Write-Host "`n=== Removing Scheduled Tasks ==="
Get-ScheduledTask | Where-Object { $_.TaskName -match "Adobe|Acrobat" } | ForEach-Object {
    try {
        Unregister-ScheduledTask -TaskName $_.TaskName -Confirm:$false -ErrorAction Stop
        Write-Host "REMOVED TASK: $($_.TaskName)"
    } catch {
        Write-Host "FAILED TASK: $($_.TaskName)"
    }
}

# 서비스 중지 및 삭제
Write-Host "`n=== Stopping Services ==="
Get-Service | Where-Object { $_.Name -match "Adobe|Acrobat" } -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        Stop-Service -Name $_.Name -Force -ErrorAction SilentlyContinue
        & sc.exe delete $_.Name 2>&1 | Out-Null
        Write-Host "REMOVED SERVICE: $($_.Name)"
    } catch {
        Write-Host "FAILED SERVICE: $($_.Name)"
    }
}

Write-Host "`n=== Done ==="
