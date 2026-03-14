Option Explicit
Dim sh, fso, base, launcher, pythonw
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base     = fso.GetParentFolderName(WScript.ScriptFullName)
launcher = base & "\launcher.pyw"

' Python313 우선 탐색 (Python314는 encodings 손상으로 제외)
Dim c(5), i
c(0) = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python313\pythonw.exe"
c(1) = "C:\Python313\pythonw.exe"
c(2) = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python312\pythonw.exe"
c(3) = "C:\Python312\pythonw.exe"
c(4) = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python311\pythonw.exe"
c(5) = "C:\Python311\pythonw.exe"
pythonw = ""
For i = 0 To 5
    If fso.FileExists(c(i)) Then pythonw = c(i) : Exit For
Next

If pythonw = "" Then
    MsgBox "pythonw.exe 를 찾을 수 없습니다." & Chr(13) & "Python 3.11 이상이 설치되어 있는지 확인하세요.", 16, "BRIDGE RPA 오류"
ElseIf Not fso.FileExists(launcher) Then
    MsgBox "launcher.pyw 를 찾을 수 없습니다." & Chr(13) & launcher, 16, "BRIDGE RPA 오류"
Else
    ' 0 = 숨김 창 (CMD 없음), False = 대기하지 않음
    sh.Run """" & pythonw & """ """ & launcher & """", 0, False
End If

Set sh = Nothing : Set fso = Nothing
