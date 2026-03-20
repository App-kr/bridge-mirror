Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

pythonExe = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe"
scriptPath = "Q:\Claudework\bridge base\tools\bridge_imagefx.py"

' Start server (minimized console — close with Ctrl+C or taskbar)
WshShell.Run """" & pythonExe & """ -X utf8 """ & scriptPath & """", 2, False

' Wait for server startup
WScript.Sleep 2500

' Find Chrome or Edge for --app mode (no URL bar, looks like a real app)
Dim browserPath
If fso.FileExists("C:\Program Files\Google\Chrome\Application\chrome.exe") Then
    browserPath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
ElseIf fso.FileExists("C:\Program Files (x86)\Google\Chrome\Application\chrome.exe") Then
    browserPath = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
ElseIf fso.FileExists("C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe") Then
    browserPath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
ElseIf fso.FileExists("C:\Program Files\Microsoft\Edge\Application\msedge.exe") Then
    browserPath = "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
Else
    browserPath = ""
End If

If browserPath <> "" Then
    WshShell.Run """" & browserPath & """ --app=http://localhost:8765", 1, False
Else
    WshShell.Run "http://localhost:8765", 1, False
End If
