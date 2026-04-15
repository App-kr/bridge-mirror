Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
strPythonEXE = "Q:\Phtyon 3\pythonw.exe"
strScript = objFSO.BuildPath(strScriptDir, "craigslist_auto_rpa.py")
strLogDir = objFSO.BuildPath(strScriptDir, "logs")

' pythonw.exe 사용 (CMD 창 없음 + tkinter 팝업만 표시)
' stdout/stderr 없음 → craigslist_auto_rpa.py 내부에서 devnull 처리
objShell.Run """" & strPythonEXE & """ -X utf8 """ & strScript & """ --headless", 0, False
