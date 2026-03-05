[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$desktop = [System.Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop "Audio Toggle.lnk"
$scriptPath = 'Q:\Claudework\bridge base\scripts\audio-toggle.ps1'

$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`""
$shortcut.WindowStyle = 7  # Minimized
$shortcut.Hotkey = "Ctrl+Alt+A"
$shortcut.IconLocation = "shell32.dll,168"
$shortcut.Description = "Toggle: Headset <-> Speaker+StandMic"
$shortcut.Save()

Write-Host "Desktop shortcut created: $shortcutPath" -ForegroundColor Green
Write-Host "Hotkey: Ctrl+Alt+A" -ForegroundColor Cyan
