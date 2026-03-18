# Adobe Service Watchdog - kills if respawned
$services = @("AGSService","AdobeARMservice","AdobeUpdateService")
foreach ($s in $services) {
    $svc = Get-Service -Name $s -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -ne "Stopped") {
        Stop-Service -Name $s -Force -ErrorAction SilentlyContinue
    }
    if ($svc) {
        Set-Service -Name $s -StartupType Disabled -ErrorAction SilentlyContinue
    }
}
$procs = @("AdobeARM","AdobeGCClient","AdobeIPCBroker","AGMService","AGSService")
foreach ($p in $procs) {
    Stop-Process -Name $p -Force -ErrorAction SilentlyContinue
}

# Kill Acrobat login popup processes
$popupProcs = @("AdobeCollabSync","AdobeIPCBroker","CCLibrary","AdobeGCClient")
foreach ($p in $popupProcs) {
    Stop-Process -Name $p -Force -ErrorAction SilentlyContinue
}
