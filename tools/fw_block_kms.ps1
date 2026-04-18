Remove-NetFirewallRule -DisplayName "BRIDGE_BLOCK_AAct_x64" -ErrorAction SilentlyContinue
Remove-NetFirewallRule -DisplayName "BRIDGE_BLOCK_KMSSS" -ErrorAction SilentlyContinue

if (Test-Path "C:\Windows\AAct_Tools\AAct_x64.exe") {
    New-NetFirewallRule -DisplayName "BRIDGE_BLOCK_AAct_x64" -Direction Outbound -Program "C:\Windows\AAct_Tools\AAct_x64.exe" -Action Block -RemoteAddress Internet -Profile Any -Enabled True | Out-Null
    Write-Host "AAct_x64.exe 인터넷 차단 완료"
} else {
    Write-Host "AAct_x64.exe 없음"
}

if (Test-Path "C:\Windows\AAct_Tools\AAct_files\KMSSS.exe") {
    New-NetFirewallRule -DisplayName "BRIDGE_BLOCK_KMSSS" -Direction Outbound -Program "C:\Windows\AAct_Tools\AAct_files\KMSSS.exe" -Action Block -RemoteAddress Internet -Profile Any -Enabled True | Out-Null
    Write-Host "KMSSS.exe 인터넷 차단 완료"
} else {
    Write-Host "KMSSS.exe 없음"
}

Write-Host ""
Write-Host "=== 적용된 방화벽 규칙 ==="
Get-NetFirewallRule -DisplayName "BRIDGE_BLOCK_AAct_x64" -ErrorAction SilentlyContinue | Select-Object DisplayName, Enabled, Action | Format-Table -AutoSize
Get-NetFirewallRule -DisplayName "BRIDGE_BLOCK_KMSSS" -ErrorAction SilentlyContinue | Select-Object DisplayName, Enabled, Action | Format-Table -AutoSize
