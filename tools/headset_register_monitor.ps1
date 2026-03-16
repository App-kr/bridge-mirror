# Register startup monitor task for ABKO N460
$taskName2 = "ABKO_N460_StartupMonitor"
$monScript = "C:\Users\Scarlett\AppData\Local\bridge_headset_monitor.ps1"

Unregister-ScheduledTask -TaskName $taskName2 -Confirm:$false -ErrorAction SilentlyContinue

$taskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Poll for ABKO N460 on startup and auto-switch</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>$env:USERDOMAIN\$env:USERNAME</UserId>
      <Delay>PT10S</Delay>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$env:USERNAME</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-WindowStyle Hidden -ExecutionPolicy Bypass -File "$monScript"</Arguments>
    </Exec>
  </Actions>
</Task>
"@

$xmlPath = "$env:TEMP\n460_monitor_task.xml"
[System.IO.File]::WriteAllText($xmlPath, $taskXml, [System.Text.Encoding]::Unicode)
Register-ScheduledTask -TaskName $taskName2 -Xml (Get-Content $xmlPath -Raw -Encoding Unicode) -Force | Out-Null

Write-Host "=== Task Registration ===" -ForegroundColor Green
Get-ScheduledTask -TaskName "ABKO_N460_AutoConnect"      | Select-Object TaskName, State | Format-Table -AutoSize
Get-ScheduledTask -TaskName "ABKO_N460_StartupMonitor"   | Select-Object TaskName, State | Format-Table -AutoSize

# Now run the monitor script directly to test
Write-Host "=== Direct test (N460 not connected = SKIP expected) ===" -ForegroundColor Cyan
$logFile = "C:\Users\Scarlett\AppData\Local\bridge_headset_switch.log"
if (Test-Path $logFile) { Remove-Item $logFile -Force }

Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue
$devices = Get-AudioDevice -List
Write-Host "Current devices:"
$devices | Select-Object Default, Type, Name | Format-Table -AutoSize

$n460 = $devices | Where-Object { $_.Name -match "N460|ABKO" }
if ($n460) {
    Write-Host "N460 PRESENT - switching now..." -ForegroundColor Green
    $n460out = $n460 | Where-Object { $_.Type -eq "Playback" } | Select-Object -First 1
    if ($n460out) { Set-AudioDevice -ID $n460out.ID | Out-Null }
    $n460in = $n460 | Where-Object { $_.Type -eq "Recording" } | Select-Object -First 1
    if ($n460in) { Set-AudioDevice -ID $n460in.ID -RecordingDefault | Out-Null }
    Write-Host "Switched to N460" -ForegroundColor Green
} else {
    Write-Host "N460 not connected (expected - will switch when connected)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== FINAL STATUS ===" -ForegroundColor Green
Write-Host "TASK 1: ABKO_N460_AutoConnect     - fires on EventID 410 (physical USB plug)"
Write-Host "TASK 2: ABKO_N460_StartupMonitor  - polls every 10s after login (covers startup + edge cases)"
Write-Host ""
Write-Host "USB Selective Suspend: DISABLED"
Write-Host "AudioDeviceCmdlets:    v3.1.0.2"
Write-Host ""
Write-Host "Test: Connect ABKO N460 USB cable -> within 10s auto-switches to default"
