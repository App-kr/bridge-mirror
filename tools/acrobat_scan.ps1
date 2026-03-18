$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== Running Adobe/Acrobat Processes ==="
Get-Process | Where-Object {
    $_.Name -like "*acro*" -or $_.Name -like "*adobe*" -or
    $_.Name -like "*AGM*" -or $_.Name -like "*NGL*" -or
    $_.Name -like "*Creative*" -or $_.Name -like "*CCLib*"
} | Select-Object Id, Name, Path | Format-Table -AutoSize

Write-Host "`n=== Registry AutoRun HKLM ==="
$hklmRun = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue
$hklmRun.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" -and ($_.Value -like "*adobe*" -or $_.Value -like "*acro*") } | ForEach-Object { Write-Host "$($_.Name) = $($_.Value)" }

Write-Host "`n=== Registry AutoRun HKCU ==="
$hkcuRun = Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue
$hkcuRun.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" -and ($_.Value -like "*adobe*" -or $_.Value -like "*acro*") } | ForEach-Object { Write-Host "$($_.Name) = $($_.Value)" }

Write-Host "`n=== Registry AutoRun WOW64 ==="
$wow64Run = Get-ItemProperty "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue
$wow64Run.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" -and ($_.Value -like "*adobe*" -or $_.Value -like "*acro*") } | ForEach-Object { Write-Host "$($_.Name) = $($_.Value)" }

Write-Host "`n=== Startup Folders ==="
Get-ChildItem "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup" -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*adobe*" -or $_.Name -like "*acro*" } | Select-Object Name, FullName
$userStartup = [System.Environment]::GetFolderPath("Startup")
Get-ChildItem $userStartup -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*adobe*" -or $_.Name -like "*acro*" } | Select-Object Name, FullName

Write-Host "`n=== ALL Scheduled Tasks (Adobe) ==="
Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object {
    $_.TaskName -like "*acro*" -or $_.TaskName -like "*adobe*" -or
    $_.TaskPath -like "*acro*" -or $_.TaskPath -like "*adobe*"
} | Select-Object TaskPath, TaskName, State | Format-Table -AutoSize

Write-Host "`n=== Run Once Keys ==="
$runonce = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce" -ErrorAction SilentlyContinue
$runonce.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" } | ForEach-Object { Write-Host "$($_.Name) = $($_.Value)" }

Write-Host "`n=== Acrobat Install Location ==="
Get-ChildItem "C:\Program Files\Adobe" -ErrorAction SilentlyContinue | Select-Object Name
Get-ChildItem "C:\Program Files (x86)\Adobe" -ErrorAction SilentlyContinue | Select-Object Name
