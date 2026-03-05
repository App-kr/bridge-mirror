# audio-toggle.ps1
# Captain 780LITE <-> Speaker+StandMic 토글
# 결과를 stdout으로 반환 (AHK가 읽어서 오버레이 표시)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Import-Module AudioDeviceCmdlets

$devices = Get-AudioDevice -List
$current = Get-AudioDevice -Playback

if ($current.Name -like "*Captain*") {
    $speaker = $devices | Where-Object { $_.Type -eq "Playback" -and $_.Name -like "*High Definition Audio Device*" -and $_.Name -notlike "*NVIDIA*" -and $_.Name -notlike "*Digital*" }
    $mic = $devices | Where-Object { $_.Type -eq "Recording" -and $_.Name -like "*stand*" }
    if ($speaker) { Set-AudioDevice -Index $speaker.Index | Out-Null }
    if ($mic) { Set-AudioDevice -Index $mic.Index | Out-Null }
    Write-Output "SPEAKER"
} else {
    $headsetSpk = $devices | Where-Object { $_.Type -eq "Playback" -and $_.Name -like "*Captain*" }
    $headsetMic = $devices | Where-Object { $_.Type -eq "Recording" -and $_.Name -like "*Captain*" }
    if ($headsetSpk) { Set-AudioDevice -Index $headsetSpk.Index | Out-Null }
    if ($headsetMic) { Set-AudioDevice -Index $headsetMic.Index | Out-Null }
    Write-Output "HEADSET"
}
