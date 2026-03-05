[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Import-Module AudioDeviceCmdlets

# Monitor Captain 780LITE mic for 10 seconds to see if peak meter behaves differently when off
$devices = Get-AudioDevice -List
$headsetMic = $devices | Where-Object { $_.Type -eq "Recording" -and $_.Name -like "*Captain*" }

if (-not $headsetMic) {
    Write-Host "Captain 780LITE mic not found!" -ForegroundColor Red
    exit
}

Write-Host "Monitoring Captain 780LITE mic peak meter for 10 seconds..." -ForegroundColor Cyan
Write-Host "(Headset is currently OFF)" -ForegroundColor Yellow

$dev = $headsetMic.Device
$errorCount = 0

for ($i = 0; $i -lt 20; $i++) {
    try {
        $meter = $dev.AudioMeterInformation
        $peak = $meter.MasterPeakValue
        $vol = $dev.AudioEndpointVolume
        $mute = $vol.Mute
        $level = $vol.MasterVolumeLevel
        $levelScalar = $vol.MasterVolumeLevelScalar
        Write-Host "  [$i] Peak: $peak | Mute: $mute | Volume: $levelScalar | dB: $level"
    } catch {
        $errorCount++
        Write-Host "  [$i] ERROR: $($_.Exception.Message)" -ForegroundColor Red
    }
    Start-Sleep -Milliseconds 500
}

Write-Host "`nErrors: $errorCount / 20" -ForegroundColor $(if ($errorCount -gt 0) { 'Red' } else { 'Green' })
