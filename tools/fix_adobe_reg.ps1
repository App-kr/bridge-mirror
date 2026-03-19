$keys = @(
    "HKLM:\SOFTWARE\Adobe",
    "HKLM:\SOFTWARE\Adobe\Adobe ARM",
    "HKLM:\SOFTWARE\Adobe\Adobe ARM\Legacy",
    "HKLM:\SOFTWARE\Adobe\Adobe ARM\Legacy\Acrobat",
    "HKLM:\SOFTWARE\Adobe\Adobe ARM\Legacy\Acrobat\{AC76BA86-1033-FFFF-7760-0C0F074F4100}",
    "HKLM:\SOFTWARE\WOW6432Node\Adobe",
    "HKLM:\SOFTWARE\WOW6432Node\Adobe\Adobe ARM",
    "HKLM:\SOFTWARE\WOW6432Node\Adobe\Adobe ARM\Legacy",
    "HKLM:\SOFTWARE\WOW6432Node\Adobe\Adobe ARM\Legacy\Acrobat",
    "HKLM:\SOFTWARE\WOW6432Node\Adobe\Adobe ARM\Legacy\Acrobat\{AC76BA86-1033-FFFF-7760-0C0F074F4100}"
)

$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$rule = New-Object System.Security.AccessControl.RegistryAccessRule(
    $user,
    "FullControl",
    "ContainerInherit,ObjectInherit",
    "None",
    "Allow"
)

foreach ($key in $keys) {
    try {
        if (-not (Test-Path $key)) {
            New-Item -Path $key -Force | Out-Null
            Write-Host "Created: $key"
        }
        $acl = Get-Acl $key
        $acl.SetAccessRule($rule)
        Set-Acl -Path $key -AclObject $acl
        Write-Host "Fixed:   $key"
    } catch {
        Write-Host "FAIL:    $key - $($_.Exception.Message)"
    }
}

Write-Host "`nDone - click Retry in installer"
