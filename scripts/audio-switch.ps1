# audio-switch.ps1
# Captain 780LITE 헤드셋 자동 전환 스크립트
# 헤드셋 ON → Captain 780LITE (스피커+마이크)
# 헤드셋 OFF → High Definition Audio Device (스피커) + stand마이크(K66)

Import-Module AudioDeviceCmdlets

$HeadsetName = "Captain 780LITE"
$FallbackPlayback = "High Definition Audio Device"
$FallbackRecording = "stand마이크(K66)"

$lastState = $null

Write-Host "[Audio Switch] Monitoring started - $(Get-Date)" -ForegroundColor Cyan
Write-Host "[Audio Switch] Headset: $HeadsetName" -ForegroundColor Gray
Write-Host "[Audio Switch] Fallback Speaker: $FallbackPlayback" -ForegroundColor Gray
Write-Host "[Audio Switch] Fallback Mic: $FallbackRecording" -ForegroundColor Gray

while ($true) {
    try {
        $devices = Get-AudioDevice -List
        $headsetPlayback = $devices | Where-Object { $_.Type -eq "Playback" -and $_.Name -like "*$HeadsetName*" }
        $headsetRecording = $devices | Where-Object { $_.Type -eq "Recording" -and $_.Name -like "*$HeadsetName*" }
        $headsetConnected = ($null -ne $headsetPlayback)

        if ($headsetConnected -and $lastState -ne "headset") {
            # Headset just connected - switch to headset
            Set-AudioDevice -Index $headsetPlayback.Index | Out-Null
            if ($headsetRecording) {
                Set-AudioDevice -Index $headsetRecording.Index | Out-Null
            }
            $lastState = "headset"
            Write-Host "[Audio Switch] $(Get-Date -Format 'HH:mm:ss') Headset CONNECTED → Captain 780LITE" -ForegroundColor Green
        }
        elseif (-not $headsetConnected -and $lastState -ne "speaker") {
            # Headset disconnected - switch to fallback
            $fbPlayback = $devices | Where-Object { $_.Type -eq "Playback" -and $_.Name -like "*$FallbackPlayback*" }
            $fbRecording = $devices | Where-Object { $_.Type -eq "Recording" -and $_.Name -like "*$FallbackRecording*" }

            if ($fbPlayback) {
                Set-AudioDevice -Index $fbPlayback.Index | Out-Null
            }
            if ($fbRecording) {
                Set-AudioDevice -Index $fbRecording.Index | Out-Null
            }
            $lastState = "speaker"
            Write-Host "[Audio Switch] $(Get-Date -Format 'HH:mm:ss') Headset DISCONNECTED → Speaker + Stand Mic" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "[Audio Switch] Error: $($_.Exception.Message)" -ForegroundColor Red
    }

    Start-Sleep -Seconds 3
}
