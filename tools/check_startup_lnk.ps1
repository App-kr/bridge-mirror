# Check startup folder shortcuts and their targets
$startupPaths = @(
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup",
    "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup"
)

foreach ($path in $startupPaths) {
    Write-Host "=== Startup folder: $path ==="
    if (Test-Path $path) {
        $items = Get-ChildItem $path -ErrorAction SilentlyContinue
        if ($items) {
            foreach ($item in $items) {
                Write-Host "File: $($item.Name) | Modified: $($item.LastWriteTime)"
                if ($item.Extension -eq ".lnk") {
                    try {
                        $shell = New-Object -ComObject WScript.Shell
                        $lnk = $shell.CreateShortcut($item.FullName)
                        Write-Host "  Target: $($lnk.TargetPath)"
                        Write-Host "  Arguments: $($lnk.Arguments)"
                        Write-Host "  WorkDir: $($lnk.WorkingDirectory)"
                    } catch {
                        Write-Host "  Could not read: $_"
                    }
                }
            }
        } else {
            Write-Host "(empty)"
        }
    } else {
        Write-Host "(not found)"
    }
    Write-Host ""
}

# Check RunOnce
Write-Host "=== HKCU RunOnce ==="
Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== HKLM RunOnce ==="
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce" -ErrorAction SilentlyContinue

# Look for nxTS
Write-Host ""
Write-Host "=== nxTS process info ==="
if (Test-Path "C:\Program Files (x86)\nxTS") {
    Get-ChildItem "C:\Program Files (x86)\nxTS" -ErrorAction SilentlyContinue | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize
}

# Check if any .vbs files are in unusual places
Write-Host ""
Write-Host "=== VBS files in user profile startup-related paths ==="
@(
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup",
    "$env:USERPROFILE\Desktop",
    "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup"
) | ForEach-Object {
    if (Test-Path $_) {
        Get-ChildItem $_ -Filter "*.vbs" -ErrorAction SilentlyContinue |
            Select-Object FullName, LastWriteTime | Format-Table -AutoSize
    }
}
