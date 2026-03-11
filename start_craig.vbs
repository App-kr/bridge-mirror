Option Explicit
Dim sh, fso, base, pythonw, i
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)

' pythonw.exe 탐지
Dim c(3)
c(0) = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python312\pythonw.exe"
c(1) = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python311\pythonw.exe"
c(2) = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python310\pythonw.exe"
c(3) = "C:\Python312\pythonw.exe"
pythonw = "pythonw.exe"
For i = 0 To 3
    If fso.FileExists(c(i)) Then pythonw = c(i) : Exit For
Next

' RPA 실행 — 창 없음 (0 = SW_HIDE), False = 비동기
sh.Run """" & pythonw & """ """ & base & "\craigslist_auto_rpa.py"" --no-relaunch", 0, False

Set sh = Nothing : Set fso = Nothing
