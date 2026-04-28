$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== All Python313 pythonw.exe instances + their full CmdLine ==="
Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -like '*Python313*pythonw.exe' -or
    ($_.Name -eq 'pythonw.exe' -and $_.CommandLine -like '*Python313*')
} | ForEach-Object {
    Write-Host ""
    Write-Host ("PID: {0}" -f $_.ProcessId)
    Write-Host ("Path: {0}" -f $_.ExecutablePath)
    Write-Host ("Cmd:  {0}" -f $_.CommandLine)
    Write-Host ("Age:  {0} min" -f [math]::Round(((Get-Date) - $_.CreationDate).TotalMinutes, 1))
}

Write-Host ""
Write-Host "=== Captured git.exe parents that are pythonw.exe (10s) ==="
$end = (Get-Date).AddSeconds(10)
$captured = @{}
while ((Get-Date) -lt $end) {
    Get-CimInstance Win32_Process -Filter "Name='git.exe'" | ForEach-Object {
        if (-not $captured.ContainsKey($_.ProcessId)) {
            $captured[$_.ProcessId] = $true
            $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.ParentProcessId)" -ErrorAction SilentlyContinue
            if ($parent -and $parent.Name -like '*pythonw*') {
                Write-Host ("  git.exe(PID $($_.ProcessId)) <- pythonw(PID $($parent.ProcessId))")
                Write-Host ("    parent cmd: $($parent.CommandLine)")
            }
        }
    }
    Start-Sleep -Milliseconds 200
}
