Set WshShell = CreateObject("WScript.Shell")

pythonExe = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe"
scriptPath = "Q:\Claudework\bridge base\tools\bridge_imagefx.py"

' Start server (minimized console window)
WshShell.Run """" & pythonExe & """ -X utf8 """ & scriptPath & """", 2, False

' Wait for server startup
WScript.Sleep 2000

' Open prompt UI in default browser
WshShell.Run "http://localhost:8765", 1, False
