$ErrorActionPreference = "SilentlyContinue"
$prefsFile = "C:\Users\Scarlett\AppData\Roaming\Adobe\Acrobat\DC\UserPrefs\UserPrefs_Acrobat.txt"
Write-Host "=== UserPrefs TOS/IMS/Sign/Accept lines ==="
Get-Content $prefsFile | Where-Object { $_ -match "TOS|EULA|IMS|Sign|Login|TOU|Accept|terms|tos|eula|tou" }

Write-Host ""
Write-Host "=== Full UserPrefs file ==="
Get-Content $prefsFile
