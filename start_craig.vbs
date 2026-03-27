' BRIDGE Craigslist RPA Launcher
' Windows VBScript 실행기

Dim objShell, objFSO, strPath, strCmd, intExitCode
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' 스크립트 디렉토리
strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' 인자 처리 (기본값: --dry-run)
Dim args, argStr
Set args = WScript.Arguments
argStr = "--dry-run --limit 1"
If args.Count > 0 Then
    argStr = ""
    Dim i
    For i = 0 To args.Count - 1
        argStr = argStr & " """ & args(i) & """"
    Next
End If

' 명령어 실행
strCmd = "python """ & strPath & "\craigslist_auto_rpa.py""" & argStr
intExitCode = objShell.Run(strCmd, 1, True)

' 에러 확인
If intExitCode <> 0 Then
    MsgBox "RPA 실행 실패" & vbCrLf & vbCrLf & _
           "종료 코드: " & intExitCode & vbCrLf & vbCrLf & _
           "해결 방법:" & vbCrLf & _
           "1. auto_vault_setup.py 실행" & vbCrLf & _
           "2. python craigslist_auto_rpa.py --dry-run (cmd에서)" & vbCrLf & _
           "3. RPA_GUIDE.md 참조", _
           vbExclamation, "Craigslist RPA - 오류"
End If
