$ErrorActionPreference = "SilentlyContinue"

# Remove old rules first
Remove-NetFirewallRule -DisplayName "Block AdobeCollabSync*" -ErrorAction SilentlyContinue
Remove-NetFirewallRule -DisplayName "Block AdobeIPCBroker*" -ErrorAction SilentlyContinue
Remove-NetFirewallRule -DisplayName "Block CCLibrary*" -ErrorAction SilentlyContinue
Remove-NetFirewallRule -DisplayName "Block AdobeARM*" -ErrorAction SilentlyContinue
Remove-NetFirewallRule -DisplayName "Block Acrobat*" -ErrorAction SilentlyContinue

# Add new rules with correct paths
$rules = @(
    @{ Name="Block AdobeCollabSync"; Path="C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\AdobeCollabSync.exe" },
    @{ Name="Block AdobeIPCBroker";  Path="C:\Program Files (x86)\Common Files\Adobe\Adobe Desktop Common\IPCBox\AdobeIPCBroker.exe" },
    @{ Name="Block CCLibrary";       Path="C:\Program Files\Common Files\Adobe\Creative Cloud Libraries\CCLibrary.exe" },
    @{ Name="Block AdobeARM";        Path="C:\Program Files (x86)\Common Files\Adobe\ARM\1.0\AdobeARM.exe" },
    @{ Name="Block CAIHelper";       Path="C:\Program Files\Common Files\Adobe\CAI\cai-helper.exe" },
    @{ Name="Block AdobeUpdater";    Path="C:\Program Files (x86)\Common Files\Adobe\OOBE\PDApp\UWA\UpdaterStartupUtility.exe" }
)

foreach ($r in $rules) {
    New-NetFirewallRule -DisplayName $r.Name -Direction Outbound -Action Block -Program $r.Path -Enabled True | Out-Null
    New-NetFirewallRule -DisplayName "$($r.Name) IN" -Direction Inbound -Action Block -Program $r.Path -Enabled True | Out-Null
}

# Verify
Write-Host "=== Firewall Rules Verification ==="
Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*AdobeCollabSync*" -or $_.DisplayName -like "*AdobeIPCBroker*" -or $_.DisplayName -like "*CCLibrary*" } | ForEach-Object {
    $filter = $_ | Get-NetFirewallApplicationFilter
    Write-Host "  $($_.DisplayName) | $($_.Direction) | $($_.Action) | $($filter.Program)"
}
