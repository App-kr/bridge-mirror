' BRIDGE Resume Converter — 런처 v3
' 창 스타일 1(정상)로 실행 → Python 내부에서 콘솔 창 즉시 숨김
Option Explicit

Dim sh, fso, py, toolDir, launcherPath, cmd
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

toolDir      = "Q:\Claudework\bridge base\tools"
launcherPath = "Q:\Claudework\bridge base\tools\resume_converter\launcher.py"

py = "Q:\Phtyon 3\python.exe"

If Not fso.FileExists(py) Then
    MsgBox "Python not found:" & vbCrLf & py, 16, "BRIDGE Converter"
    WScript.Quit 1
End If

If Not fso.FileExists(launcherPath) Then
    MsgBox "launcher.py not found:" & vbCrLf & launcherPath, 16, "BRIDGE Converter"
    WScript.Quit 1
End If

sh.CurrentDirectory = toolDir

cmd = Chr(34) & py & Chr(34) & _
      " -X utf8 " & _
      Chr(34) & launcherPath & Chr(34)

' 창 스타일 1 = 정상 표시 (SW_SHOWNORMAL)
' Python 내부에서 콘솔 창을 즉시 숨기므로 검은 창은 안 보임
sh.Run cmd, 1, False

Set fso = Nothing
Set sh  = Nothing
