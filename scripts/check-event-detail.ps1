[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Get detailed audio events with XML data
$events = Get-WinEvent -LogName "Microsoft-Windows-Audio/Operational" -MaxEvents 30

foreach ($e in $events) {
    $xml = [xml]$e.ToXml()
    $data = $xml.Event.EventData.Data

    # Check if Captain/780LITE related
    $xmlStr = $e.ToXml()

    Write-Host "--- $($e.TimeCreated) (ID: $($e.Id)) ---" -ForegroundColor Yellow

    if ($data) {
        foreach ($d in $data) {
            $name = $d.Name
            $value = $d.'#text'
            if ($value) {
                Write-Host "  ${name}: $value"
            }
        }
    } else {
        # Try to extract key info from XML
        Write-Host "  $($e.Message)"
    }
    Write-Host ""
}
