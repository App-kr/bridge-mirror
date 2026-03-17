$WshShell = New-Object -comObject WScript.Shell
$Desktop = [Environment]::GetFolderPath('Desktop')
$Shortcut = $WshShell.CreateShortcut("$Desktop\BRIDGE Prompts.lnk")
$Shortcut.TargetPath = "Q:\Claudework\bridge base\tools\bridge_prompt_ui.html"
$Shortcut.IconLocation = "Q:\Claudework\bridge base\tools\bridge_prompt.ico"
$Shortcut.Description = "BRIDGE Image Prompt Generator"
$Shortcut.Save()
Write-Host "OK — shortcut created on Desktop"
