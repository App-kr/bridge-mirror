# WSH 에러 이벤트 로그 확인

Write-Host "--- Application Event Log: WSH/Script errors ---"
Get-WinEvent -LogName Application -MaxEvents 500 -ErrorAction SilentlyContinue |
    Where-Object { $_.ProviderName -match "WSH|Script|Wscript|Windows Script" -or
                   ($_.Id -eq 1 -and $_.ProviderName -match "WSH") } |
    Select-Object TimeCreated, Id, ProviderName, Message -First 20 | Format-List

Write-Host "--- BridgeInterviewReminder task ---"
$t = Get-ScheduledTask -TaskName 'BridgeInterviewReminder' -ErrorAction SilentlyContinue
if ($t) {
    Write-Host "State: $($t.State)"
    $t.Actions | ForEach-Object { Write-Host "Execute: $($_.Execute) | Args: $($_.Arguments)" }
    $t.Triggers | ForEach-Object { Write-Host "Trigger: $($_.CimClass.CimClassName)" }
}

Write-Host "--- BridgeBlogAuto task ---"
$t2 = Get-ScheduledTask -TaskName 'BridgeBlogAuto' -ErrorAction SilentlyContinue
if ($t2) {
    Write-Host "State: $($t2.State)"
    $t2.Actions | ForEach-Object { Write-Host "Execute: $($_.Execute) | Args: $($_.Arguments)" }
    $t2.Triggers | ForEach-Object { Write-Host "Trigger: $($_.CimClass.CimClassName)" }
}

Write-Host "--- BridgeCraig rpa_overlay.py ---"
if (Test-Path "Q:\BridgeCraig\rpa_overlay.py") {
    Get-Content "Q:\BridgeCraig\rpa_overlay.py" | Select-Object -First 40
}

Write-Host "--- Windows Script Host event log entries ---"
Get-WinEvent -LogName "Application" -MaxEvents 1000 -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match "bridge" -or $_.ProviderName -match "Script" } |
    Select-Object TimeCreated, Id, ProviderName, @{N="Msg";E={$_.Message.Substring(0,[Math]::Min(200,$_.Message.Length))}} |
    Sort-Object TimeCreated -Descending | Select-Object -First 10 | Format-Table -Wrap
