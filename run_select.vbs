' BRIDGE RPA 계정 선택 런처 (CMD창 없음)
' 아이콘 더블클릭 → 계정 선택창 → 선택 계정 순차 실행

Set objShell = CreateObject("WScript.Shell")
Set objFSO   = CreateObject("Scripting.FileSystemObject")

strDir     = objFSO.GetParentFolderName(WScript.ScriptFullName)
strPythonW = "Q:\Phtyon 3\pythonw.exe"
strScript  = objFSO.BuildPath(strDir, "rpa_select_launcher.py")

' 0 = 창 완전 숨김, False = 기다리지 않음 (런처 자체가 UI 담당)
objShell.Run """" & strPythonW & """ -X utf8 """ & strScript & """", 0, False
