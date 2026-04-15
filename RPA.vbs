Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' 현재 스크립트 디렉토리
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Python 직접 실행
strPythonEXE = "Q:\Phtyon 3\python.exe"
strScript = objFSO.BuildPath(strScriptDir, "craigslist_auto_rpa.py")

' 4개 계정 순차 실행 (True = 완료 후 다음 계정 시작)
Dim accounts(3)
accounts(0) = "account1"
accounts(1) = "account2"
accounts(2) = "account3"
accounts(3) = "account4"

Dim i
For i = 0 To 3
    strCmd = """" & strPythonEXE & """ -X utf8 """ & strScript & """ --headless --account " & accounts(i)
    objShell.Run strCmd, 1, True
Next
