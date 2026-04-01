Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File ""Q:\Claudework\bridge base\scripts\audio\audio-startup.ps1""", 0, False
Set WshShell = Nothing
