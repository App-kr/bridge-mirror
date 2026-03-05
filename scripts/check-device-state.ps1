[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Import-Module AudioDeviceCmdlets

# Check device state through MMDevice COM object
$devices = Get-AudioDevice -List
foreach ($d in $devices) {
    if ($d.Name -like "*Captain*") {
        $dev = $d.Device
        Write-Host "Name: $($d.Name)"
        Write-Host "  Index: $($d.Index)"
        Write-Host "  Type: $($d.Type)"
        Write-Host "  Default: $($d.Default)"
        Write-Host "  ID: $($d.ID)"

        # Try accessing device state
        try {
            $state = $dev.State
            Write-Host "  State: $state"
        } catch {
            Write-Host "  State: (error) $($_.Exception.Message)"
        }

        # Try accessing properties
        try {
            $props = $dev.Properties
            Write-Host "  Properties Count: $($props.Count)"
        } catch {
            Write-Host "  Properties: (error)"
        }

        # Try audio meter
        try {
            $meter = $dev.AudioMeterInformation
            $peak = $meter.MasterPeakValue
            Write-Host "  Peak Meter: $peak"
        } catch {
            Write-Host "  Peak Meter: (error) $($_.Exception.Message)"
        }

        Write-Host ""
    }
}
