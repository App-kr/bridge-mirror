' BRIDGE Craigslist RPA Launcher
' Windows VBScript 실행기

Dim objShell, objFSO, strPath, strCmd, intExitCode
Dim pythonPath, candidates, i, j, args, argStr, scriptFile

On Error Resume Next

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' 스크립트 디렉토리
strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Python 경로 찾기
pythonPath = ""

' 표준 경로 확인
candidates = Array( _
    "C:\Users\Scarlett\AppData\Local\Programs\Python\Python314\python.exe", _
    "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe", _
    "C:\Python314\python.exe", _
    "C:\Python313\python.exe" _
)

For i = 0 To UBound(candidates)
    If objFSO.FileExists(candidates(i)) Then
        pythonPath = candidates(i)
        Exit For
    End If
Next

' Python이 없으면 에러
If pythonPath = "" Then
    MsgBox "Python을 찾을 수 없습니다." & vbCrLf & vbCrLf & _
           "설치 경로:" & vbCrLf & _
           "C:\Users\Scarlett\AppData\Local\Programs\Python\Python314", _
           vbCritical, "Craigslist RPA - Python 미설치"
    WScript.Quit 1
End If

' 인자 처리
Set args = WScript.Arguments
argStr = "--dry-run --limit 1"
If args.Count > 0 Then
    argStr = ""
    For j = 0 To args.Count - 1
        argStr = argStr & " """ & args(j) & """"
    Next
End If

' 스크립트 파일 확인
scriptFile = strPath & "\craigslist_auto_rpa.py"
If Not objFSO.FileExists(scriptFile) Then
    MsgBox "파일을 찾을 수 없습니다: " & scriptFile, _
           vbCritical, "Craigslist RPA - 파일 오류"
    WScript.Quit 1
End If

' 명령어 실행
strCmd = pythonPath & " """ & scriptFile & """ " & argStr
intExitCode = objShell.Run(strCmd, 1, True)

' 에러 확인
If intExitCode <> 0 Then
    MsgBox "RPA 실행 실패" & vbCrLf & vbCrLf & _
           "종료 코드: " & intExitCode & vbCrLf & vbCrLf & _
           "해결 방법:" & vbCrLf & _
           "1. python auto_vault_setup.py" & vbCrLf & _
           "2. cmd: python craigslist_auto_rpa.py --dry-run" & vbCrLf & _
           "3. RPA_GUIDE.md 참조", _
           vbExclamation, "Craigslist RPA - 오류"
    WScript.Quit intExitCode
End If

WScript.Quit 0
