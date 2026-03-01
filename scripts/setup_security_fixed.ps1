$Port = 8501
$DBPath = "Q:\Claudework\bridge base\master.db"

Write-Host "--- BRIDGE Security Setup Starting ---" -ForegroundColor Cyan

# Firewall Rule
Remove-NetFirewallRule -DisplayName "BRIDGE_Secure_Access" -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "BRIDGE_Secure_Access" -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow -Profile Private, Domain

# File Access Control
if (Test-Path $DBPath) {
    $Acl = Get-Acl $DBPath
    $Ar = New-Object System.Security.AccessControl.FileSystemAccessRule($env:USERNAME, "FullControl", "Allow")
    $Acl.SetAccessRule($Ar)
    Set-Acl $DBPath $Acl
    Write-Host "Success: Database secured for $env:USERNAME" -ForegroundColor Green
} else {
    Write-Host "Warning: master.db not found. Please run after data loading." -ForegroundColor Yellow
}