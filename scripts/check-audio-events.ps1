[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Check recent audio/device connection events
Write-Host "=== Recent Audio Device Events ===" -ForegroundColor Cyan
try {
    Get-WinEvent -LogName "Microsoft-Windows-Audio/Operational" -MaxEvents 20 -ErrorAction SilentlyContinue |
        Select-Object TimeCreated, Id, Message |
        Format-Table -Wrap -AutoSize
} catch {
    Write-Host "Audio Operational log not available"
}

Write-Host "`n=== Device Setup Events (last 10) ===" -ForegroundColor Cyan
try {
    Get-WinEvent -LogName "Microsoft-Windows-UserPnp/DeviceInstall" -MaxEvents 10 -ErrorAction SilentlyContinue |
        Select-Object TimeCreated, Id, Message |
        Format-Table -Wrap -AutoSize
} catch {
    Write-Host "DeviceInstall log not available"
}

Write-Host "`n=== Kernel-PnP Events (Captain related) ===" -ForegroundColor Cyan
try {
    Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Device Configuration" -MaxEvents 20 -ErrorAction SilentlyContinue |
        Where-Object { $_.Message -like "*Captain*" -or $_.Message -like "*4C4A*" -or $_.Message -like "*audio*" } |
        Select-Object TimeCreated, Id, Message |
        Format-Table -Wrap -AutoSize
} catch {
    Write-Host "Kernel-PnP log not available"
}

Write-Host "`n=== System Log Audio Events ===" -ForegroundColor Cyan
try {
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='*audio*'; StartTime=(Get-Date).AddHours(-1)} -MaxEvents 10 -ErrorAction SilentlyContinue |
        Select-Object TimeCreated, ProviderName, Message |
        Format-Table -Wrap -AutoSize
} catch {
    Write-Host "No recent system audio events"
}
