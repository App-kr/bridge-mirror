# Task Scheduler trigger fix - Kernel-PnP channel
$taskName = "ABKO_N460_AutoConnect"
$switchScriptPath = "C:\Users\Scarlett\AppData\Local\bridge_headset_switch.ps1"

Write-Host "[STEP 1] Remove old task..." -ForegroundColor Cyan
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$taskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>ABKO N460 auto switch on USB connect</Description>
  </RegistrationInfo>
  <Triggers>
    <EventTrigger>
      <Enabled>true</Enabled>
      <Subscription><![CDATA[<QueryList><Query Id="0" Path="Microsoft-Windows-Kernel-PnP/Configuration"><Select Path="Microsoft-Windows-Kernel-PnP/Configuration">*[System[EventID=410]]</Select></Query></QueryList>]]></Subscription>
      <Delay>PT3S</Delay>
    </EventTrigger>
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
    <ExecutionTimeLimit>PT1M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-WindowStyle Hidden -ExecutionPolicy Bypass -File "$switchScriptPath"</Arguments>
    </Exec>
  </Actions>
</Task>
"@

$taskXmlPath = "$env:TEMP\n460_task_v2.xml"
[System.IO.File]::WriteAllText($taskXmlPath, $taskXml, [System.Text.Encoding]::Unicode)

Write-Host "[STEP 2] Register task with Kernel-PnP EventID 410 trigger..." -ForegroundColor Cyan
try {
    Register-ScheduledTask -TaskName $taskName -Xml (Get-Content $taskXmlPath -Raw -Encoding Unicode) -Force | Out-Null
    Write-Host "  [OK] Task registered" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] $_" -ForegroundColor Red
    exit 1
}

# Verify
$task = Get-ScheduledTask -TaskName $taskName
Write-Host ""
Write-Host "=== Task verified ===" -ForegroundColor Green
Write-Host "Name: $($task.TaskName) | State: $($task.State)"

# Check Kernel-PnP EventID distribution
Write-Host ""
Write-Host "[STEP 3] Check Kernel-PnP event IDs..." -ForegroundColor Cyan
$allIds = Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -MaxEvents 200 |
          Group-Object Id | Sort-Object Count -Descending | Select-Object -First 10
Write-Host "Recent event IDs in Kernel-PnP/Configuration:"
$allIds | Format-Table Name, Count -AutoSize

$has410 = Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -MaxEvents 200 |
          Where-Object { $_.Id -eq 410 } | Select-Object -First 1
if ($has410) {
    Write-Host "EventID 410 found - trigger WILL fire on device connect" -ForegroundColor Green
    Write-Host "Last 410 event: $($has410.TimeCreated)"
} else {
    Write-Host "EventID 410 not in recent 200 events - checking all available IDs above" -ForegroundColor Yellow
}

# Reset log
$logFile = "C:\Users\Scarlett\AppData\Local\bridge_headset_switch.log"
if (Test-Path $logFile) { Remove-Item $logFile -Force }
Write-Host ""
Write-Host "[READY] Log cleared. Connect ABKO N460 USB to test auto-switch." -ForegroundColor Yellow
