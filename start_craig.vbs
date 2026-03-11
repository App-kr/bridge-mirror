Dim oShell, oFS, pythonw, script
Set oShell = CreateObject("WScript.Shell")
Set oFS    = CreateObject("Scripting.FileSystemObject")

script = "Q:\Claudework\bridge base\craigslist_auto_rpa.py"

' pythonw.exe 자동 탐지 (312 → 311 → 310 순)
Dim versions(2), i, candidate
versions(0) = "312"
versions(1) = "311"
versions(2) = "310"
pythonw = ""

For i = 0 To 2
    candidate = oShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & _
                "\Programs\Python\Python" & versions(i) & "\pythonw.exe"
    If oFS.FileExists(candidate) Then
        pythonw = candidate
        Exit For
    End If
    ' 시스템 설치 경로도 확인
    candidate = "C:\Python" & versions(i) & "\pythonw.exe"
    If oFS.FileExists(candidate) Then
        pythonw = candidate
        Exit For
    End If
Next

If pythonw = "" Then
    MsgBox "Python 3.10 / 3.11 / 3.12 를 찾을 수 없습니다." & vbCrLf & _
           "Python 설치 후 다시 실행해주세요.", vbCritical, "BRIDGE RPA"
Else
    ' SW_HIDE = 0 → CMD 창 없이 완전 숨김 실행
    oShell.Run Chr(34) & pythonw & Chr(34) & " " & Chr(34) & script & Chr(34), 0, False
End If
