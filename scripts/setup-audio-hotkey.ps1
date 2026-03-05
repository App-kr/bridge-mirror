[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ahkExe = 'Q:\Claudework\bridge base\tools\autohotkey\AutoHotkey64.exe'
$ahkScript = 'Q:\Claudework\bridge base\scripts\audio-toggle.ahk'
$startupFolder = [System.Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupFolder "AudioToggle.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $ahkExe
$shortcut.Arguments = "`"$ahkScript`""
$shortcut.WorkingDirectory = 'Q:\Claudework\bridge base\scripts'
$shortcut.Description = "Audio Toggle: Ctrl+Shift+- (headset/speaker)"
$shortcut.Save()

Write-Host "Startup shortcut created: $shortcutPath" -ForegroundColor Green
