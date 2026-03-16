# Check Application event log for WSH/wscript errors
Write-Host "=== Application Log - WSH/Script errors ==="
Get-WinEvent -LogName "Application" -MaxEvents 500 -ErrorAction SilentlyContinue |
    Where-Object {
        $_.ProviderName -match "WSH|Windows Script Host|VBScript|WScript" -or
        ($_.Message -match "파일 확장자|file extension|wscript" -and $_.Level -le 3)
    } |
    Select-Object TimeCreated, ProviderName, Id, @{N="Msg";E={$_.Message.Substring(0, [Math]::Min(200, $_.Message.Length))}} |
    Sort-Object TimeCreated -Descending |
    Select-Object -First 20 |
    Format-Table -AutoSize -Wrap

Write-Host ""
Write-Host "=== Application Log - Errors/Warnings today ==="
Get-WinEvent -LogName "Application" -ErrorAction SilentlyContinue |
    Where-Object {
        $_.TimeCreated -gt (Get-Date).AddHours(-12) -and
        $_.Level -le 2
    } |
    Select-Object TimeCreated, ProviderName, Id, @{N="Msg";E={$_.Message.Substring(0, [Math]::Min(150, $_.Message.Length))}} |
    Sort-Object TimeCreated -Descending |
    Select-Object -First 30 |
    Format-Table -AutoSize -Wrap

Write-Host ""
Write-Host "=== System Log - errors today ==="
Get-WinEvent -LogName "System" -ErrorAction SilentlyContinue |
    Where-Object {
        $_.TimeCreated -gt (Get-Date).AddHours(-12) -and
        $_.Level -le 2
    } |
    Select-Object TimeCreated, ProviderName, Id, @{N="Msg";E={$_.Message.Substring(0, [Math]::Min(150, $_.Message.Length))}} |
    Sort-Object TimeCreated -Descending |
    Select-Object -First 20 |
    Format-Table -AutoSize -Wrap
