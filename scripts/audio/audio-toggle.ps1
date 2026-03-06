# audio-toggle.ps1
# Captain 780LITE <-> Speaker+StandMic 토글

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Import-Module AudioDeviceCmdlets

$devices = Get-AudioDevice -List
$current = Get-AudioDevice -Playback
$captainExists = $devices | Where-Object { $_.Type -eq "Playback" -and $_.Name -like "*Captain*" }

if ($current.Name -like "*Captain*") {
    # Currently headset -> switch to speaker
    $speaker = $devices | Where-Object { $_.Type -eq "Playback" -and $_.Name -like "*High Definition Audio Device*" -and $_.Name -notlike "*NVIDIA*" -and $_.Name -notlike "*Digital*" }
    $mic = $devices | Where-Object { $_.Type -eq "Recording" -and $_.Name -like "*stand*" }
    if ($speaker) { Set-AudioDevice -Index $speaker.Index | Out-Null }
    if ($mic) { Set-AudioDevice -Index $mic.Index | Out-Null }
    Write-Output "SPEAKER"
} elseif ($captainExists) {
    # Currently speaker, headset available -> switch to headset
    $headsetMic = $devices | Where-Object { $_.Type -eq "Recording" -and $_.Name -like "*Captain*" }
    Set-AudioDevice -Index $captainExists.Index | Out-Null
    if ($headsetMic) { Set-AudioDevice -Index $headsetMic.Index | Out-Null }
    Write-Output "HEADSET"
} else {
    # Headset not available
    Write-Output "NO_HEADSET"
}
