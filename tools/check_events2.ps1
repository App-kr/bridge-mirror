# Simpler event log check
try {
    $events = Get-WinEvent -LogName "Application" -MaxEvents 200 -ErrorAction SilentlyContinue
    Write-Host "App log event count: $($events.Count)"

    # Look for any WSH or script errors
    $wsh = $events | Where-Object {
        $p = $_.ProviderName
        $p -eq "WSH" -or $p -like "*Script*" -or $p -like "*VBScript*"
    }
    Write-Host "WSH/Script events: $($wsh.Count)"
    $wsh | Select-Object TimeCreated, ProviderName, Id | Format-Table

    # Look for recent errors
    $errs = $events | Where-Object { $_.Level -le 2 -and $_.TimeCreated -gt (Get-Date).AddDays(-1) }
    Write-Host "Recent errors/criticals (24h): $($errs.Count)"
    $errs | Select-Object TimeCreated, ProviderName, Id | Sort-Object TimeCreated -Descending | Select-Object -First 20 | Format-Table

} catch {
    Write-Host "Error: $_"
}
