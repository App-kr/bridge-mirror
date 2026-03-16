$procs = Get-WmiObject Win32_Process | Where-Object Name -like "python*"
foreach ($p in $procs) {
    Write-Output ("PID=" + $p.ProcessId + " | CMD=" + $p.CommandLine)
}
