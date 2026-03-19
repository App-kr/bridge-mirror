$installer = "C:\Users\Scarlett\Desktop\Adobe Acrobat Pro DC.exe"
$installPath = "G:\Adobe"

if (-not (Test-Path $installPath)) {
    New-Item -ItemType Directory -Path $installPath -Force | Out-Null
}

Write-Host "Installing silently to $installPath ..."

# /sAll = silent, /rs = suppress reboot, /rps = suppress reboot prompt
# IGNOREDEPCHECK=1 = ignore dependency check errors
# IGNOREVCRT64=1 = ignore visual C++ runtime errors
Start-Process -FilePath $installer `
    -ArgumentList "/sAll", "/rs", "/rps", "/msi", `
        "INSTALLLOCATION=`"$installPath`"", `
        "ALLUSERS=1", `
        "IGNOREDEPCHECK=1" `
    -Wait -NoNewWindow

Write-Host "Process finished. Checking G drive..."
Get-ChildItem "G:\" | Format-Table Name
