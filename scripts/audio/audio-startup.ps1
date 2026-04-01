[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$logDir = "Q:\Claudework\bridge base\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = "$logDir\audio-startup.log"

function Log($msg) {
    $ts = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    Add-Content -Path $logFile -Value "[$ts] $msg" -Encoding UTF8
}

Import-Module AudioDeviceCmdlets

$devices = Get-AudioDevice -List

$speaker = $devices | Where-Object {
    $_.Type -eq "Playback" -and
    $_.Name -like "*High Definition Audio Device*" -and
    $_.Name -notlike "*NVIDIA*" -and
    $_.Name -notlike "*Digital*"
}

$standMic = $devices | Where-Object {
    $_.Type -eq "Recording" -and
    $_.Name -like "*stand*"
}

if ($speaker) {
    Set-AudioDevice -Index $speaker.Index | Out-Null
    Log "Speaker set: $($speaker.Name)"
}

if ($standMic) {
    Set-AudioDevice -Index $standMic.Index | Out-Null
    Log "Mic set: $($standMic.Name)"
}

Log "Done"

$monitorScript = "Q:\Claudework\bridge base\scripts\audio\audio-monitor.ps1"
if (Test-Path $monitorScript) {
    $wsh = New-Object -ComObject WScript.Shell
    $wsh.Run("powershell.exe -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File `"$monitorScript`"", 0, $false)
    Log "Monitor started - USB detection active"
} else {
    Log "WARNING: audio-monitor.ps1 not found"
}
