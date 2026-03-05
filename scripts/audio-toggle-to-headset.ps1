[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Import-Module AudioDeviceCmdlets
$devices = Get-AudioDevice -List
$hs = $devices | Where-Object { $_.Type -eq "Playback" -and $_.Name -like "*Captain*" }
$hm = $devices | Where-Object { $_.Type -eq "Recording" -and $_.Name -like "*Captain*" }
if ($hs) { Set-AudioDevice -Index $hs.Index | Out-Null }
if ($hm) { Set-AudioDevice -Index $hm.Index | Out-Null }
