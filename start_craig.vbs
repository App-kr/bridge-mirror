Option Explicit
Dim sh, fso, base, ps1
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
ps1  = base & "\scripts\launch_now.ps1"

If fso.FileExists(ps1) Then
    sh.Run "powershell.exe -ExecutionPolicy Bypass -File """ & ps1 & """", 1, False
Else
    MsgBox "launch_now.ps1 을 찾을 수 없습니다." & Chr(13) & ps1, 16, "BRIDGE RPA 오류"
End If

Set sh = Nothing : Set fso = Nothing
