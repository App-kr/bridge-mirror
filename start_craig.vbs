Option Explicit
Dim sh, fso, base, pythonw
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)

' python 설치 경로에서 pythonw.exe 자동 탐지
Dim c(5), i
c(0) = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python313\pythonw.exe"
c(1) = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python312\pythonw.exe"
c(2) = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python311\pythonw.exe"
c(3) = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python310\pythonw.exe"
c(4) = "C:\Python312\pythonw.exe"
c(5) = "C:\Python311\pythonw.exe"
pythonw = ""
For i = 0 To 5
    If fso.FileExists(c(i)) Then pythonw = c(i) : Exit For
Next

' pythonw.exe 못 찾으면 where 명령으로 탐지
If pythonw = "" Then
    Dim found
    found = sh.ExpandEnvironmentStrings("%TEMP%") & "\pw_path.txt"
    sh.Run "cmd /c where pythonw.exe > """ & found & """", 0, True
    If fso.FileExists(found) Then
        Dim ts : Set ts = fso.OpenTextFile(found, 1)
        If Not ts.AtEndOfStream Then pythonw = Trim(ts.ReadLine())
        ts.Close
        fso.DeleteFile found
    End If
End If

' pythonw.exe 로 직접 실행 — CMD 창 없음
If pythonw <> "" Then
    sh.Run """" & pythonw & """ """ & base & "\craigslist_auto_rpa.py"" --no-relaunch", 0, False
Else
    MsgBox "pythonw.exe 를 찾을 수 없습니다." & Chr(13) & "Python 이 설치되어 있는지 확인하세요.", 16, "BRIDGE RPA 오류"
End If

Set sh = Nothing : Set fso = Nothing
