$ErrorActionPreference = "SilentlyContinue"
Write-Host "=== Adobe TOS / EULA Registry Scan ==="

$paths = @(
    "HKCU:\SOFTWARE\Adobe\Adobe Acrobat\DC\AdobeViewer",
    "HKCU:\SOFTWARE\Adobe\Adobe Acrobat\DC\AVGeneral",
    "HKCU:\SOFTWARE\Adobe\Acrobat Reader\DC\AdobeViewer",
    "HKCU:\SOFTWARE\Adobe\Acrobat Reader\DC\AVGeneral",
    "HKLM:\SOFTWARE\Adobe\Adobe Acrobat\DC\AdobeViewer",
    "HKLM:\SOFTWARE\WOW6432Node\Adobe\Adobe Acrobat\DC\AdobeViewer",
    "HKLM:\SOFTWARE\Policies\Adobe\Adobe Acrobat\DC\FeatureLockDown",
    "HKCU:\SOFTWARE\Adobe\CommonFiles\Usage",
    "HKCU:\SOFTWARE\Adobe\Adobe Acrobat\DC\Installer",
    "HKLM:\SOFTWARE\Adobe\Adobe Acrobat\DC\Installer"
)

foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Host "`n[$p]"
        Get-ItemProperty $p | ForEach-Object {
            $_.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" } | ForEach-Object {
                Write-Host "  $($_.Name) = $($_.Value)"
            }
        }
    }
}

Write-Host "`n=== Search TOS/EULA keys across Adobe hive ==="
@("HKCU:\SOFTWARE\Adobe", "HKLM:\SOFTWARE\Adobe", "HKLM:\SOFTWARE\WOW6432Node\Adobe") | ForEach-Object {
    Get-ChildItem $_ -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
        $props = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
        if ($props) {
            $props.PSObject.Properties | Where-Object {
                $_.Name -match "TOS|EULA|Terms|Accept|Compliant|bDisplay" -and $_.Name -notlike "PS*"
            } | ForEach-Object {
                Write-Host "  $($props.PSPath) :: $($_.Name) = $($_.Value)"
            }
        }
    }
}
