[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Import-Module AudioDeviceCmdlets

$logDir = "Q:\Claudework\bridge base\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = "$logDir\audio-monitor.log"

function Log($msg) {
    $ts = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    Add-Content -Path $logFile -Value "[$ts] $msg" -Encoding UTF8
}

function Signal($type) {
    $signalDir = "Q:\Claudework\bridge base\scripts\audio"
    if ($type -eq "headset") {
        "" | Out-File -FilePath "$signalDir\signal-headset-on.txt" -Encoding UTF8 -Force
    } elseif ($type -eq "speaker") {
        "" | Out-File -FilePath "$signalDir\signal-speaker-on.txt" -Encoding UTF8 -Force
    }
}

function SwitchToHeadset {
    try {
        $devices = Get-AudioDevice -List
        $headset = $devices | Where-Object { $_.Type -eq "Playback" -and $_.Name -like "*Captain*" }
        $headsetMic = $devices | Where-Object { $_.Type -eq "Recording" -and $_.Name -like "*Captain*" }

        if ($headset) { Set-AudioDevice -Index $headset.Index | Out-Null }
        if ($headsetMic) { Set-AudioDevice -Index $headsetMic.Index | Out-Null }

        if ($headset -or $headsetMic) {
            Signal "headset"
            Log "OK: Captain 780 activated"
        }
    } catch {
        Log "ERROR: headset switch failed - $_"
    }
}

function SwitchToSpeaker {
    try {
        $devices = Get-AudioDevice -List
        $speaker = $devices | Where-Object {
            $_.Type -eq "Playback" -and
            $_.Name -like "*High Definition Audio Device*" -and
            $_.Name -notlike "*NVIDIA*" -and
            $_.Name -notlike "*Digital*"
        }
        $mic = $devices | Where-Object { $_.Type -eq "Recording" -and $_.Name -like "*stand*" }

        if ($speaker) { Set-AudioDevice -Index $speaker.Index | Out-Null }
        if ($mic) { Set-AudioDevice -Index $mic.Index | Out-Null }

        if ($speaker -or $mic) {
            Signal "speaker"
            Log "OK: Speaker + Stand K66 activated"
        }
    } catch {
        Log "ERROR: speaker switch failed - $_"
    }
}

Log "=== USB Monitor Started (WMI Event) ==="

$lastState = $null

# WMI event-based USB detection
$query = "SELECT * FROM Win32_DeviceChangeEvent WHERE EventType = 2 OR EventType = 3"

Register-WmiEvent -Query $query -SourceIdentifier "USBChange" -Action {
    Start-Sleep -Milliseconds 800

    $devices = Get-AudioDevice -List
    $headsetNow = [bool]($devices | Where-Object { $_.Type -eq "Playback" -and $_.Name -like "*Captain*" })

    if ($headsetNow) {
        SwitchToHeadset
    } else {
        SwitchToSpeaker
    }
} | Out-Null

Log "WMI listener registered - waiting for USB events"

# Keep running
while ($true) {
    Start-Sleep -Seconds 60
}
