$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== [A] Storage Sense ===" -ForegroundColor Cyan
$ss = Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy" -ErrorAction SilentlyContinue
if ($ss) {
    Write-Host "StorageSense Active: $($ss.'01')"
    Write-Host "Temp App Files: $($ss.'256')"
    Write-Host "Downloads Folder: $($ss.'512')"
    Write-Host "LocalAppData: $($ss.'2048')"
} else {
    Write-Host "Storage Sense not configured"
}

Write-Host ""
Write-Host "=== [B] Security Software ===" -ForegroundColor Cyan
Get-ItemProperty "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*" -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -imatch "antivirus|security|defend|protect|avast|avg|kasper|norton|mcafee|eset|bitdef|malware|ahnlab|avira|sophos|360" } |
    Select-Object DisplayName, Publisher |
    Format-Table -AutoSize

Write-Host "=== [C] SharedPC Kiosk Mode ===" -ForegroundColor Cyan
$kiosk = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\SharedPC" -ErrorAction SilentlyContinue
if ($kiosk) {
    Write-Host "SharedPC mode FOUND:"
    $kiosk | Format-List
} else {
    Write-Host "SharedPC mode: NOT found (normal)"
}

Write-Host ""
Write-Host "=== [D] Startup Registry Entries ===" -ForegroundColor Cyan
$runKeys = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"
)
foreach ($key in $runKeys) {
    $items = Get-ItemProperty $key -ErrorAction SilentlyContinue
    if ($items) {
        $items.PSObject.Properties | Where-Object { $_.Name -notmatch "^PS" } | ForEach-Object {
            Write-Host "  [$($key.Split('\')[-1])] $($_.Name) = $($_.Value)"
        }
    }
}

Write-Host ""
Write-Host "=== [E] Chrome Event Logs ===" -ForegroundColor Cyan
Get-WinEvent -LogName "Application" -MaxEvents 300 -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -imatch "chrome" -or $_.ProviderName -imatch "chrome" } |
    Select-Object TimeCreated, Id, LevelDisplayName, @{N='Msg';E={$_.Message.Substring(0,[math]::Min(100,$_.Message.Length))}} |
    Select-Object -First 8 |
    Format-List

Write-Host ""
Write-Host "=== [F] Windows Defender Recent Actions ===" -ForegroundColor Cyan
Get-WinEvent -LogName "Microsoft-Windows-Windows Defender/Operational" -MaxEvents 20 -ErrorAction SilentlyContinue |
    Where-Object { $_.LevelDisplayName -imatch "Warning|Error" -or $_.Id -in @(1006,1007,1008,1116,1117,1118,1119) } |
    Select-Object TimeCreated, Id, @{N='Msg';E={$_.Message.Substring(0,[math]::Min(150,$_.Message.Length))}} |
    Format-List

Write-Host "Diag2 done."
