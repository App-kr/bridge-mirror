Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' 현재 스크립트 디렉토리
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Python 직접 실행 (cmd 창 없음)
strPythonEXE = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe"
strScript = objFSO.BuildPath(strScriptDir, "craigslist_auto_rpa.py")

' 백그라운드 실행 (0 = 숨김, True = 대기 없음)
objShell.Run """" & strPythonEXE & """ -X utf8 """ & strScript & """", 0, False
