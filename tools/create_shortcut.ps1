# BX Credential Manager 바탕화면 바로가기 생성
$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$Desktop\BX Credential Manager.lnk")
$Shortcut.TargetPath = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\pythonw.exe"
$Shortcut.Arguments = '-X utf8 "Q:\Claudework\bridge base\tools\pw.py"'
$Shortcut.WorkingDirectory = "Q:\Claudework\bridge base\tools"
$Shortcut.IconLocation = "Q:\Claudework\bridge base\tools\bx_icon.ico,0"
$Shortcut.Description = "BX Credential Manager - Password & API Key Manager"
$Shortcut.Save()
Write-Host "Desktop shortcut created: $Desktop\BX Credential Manager.lnk"
