Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' 현재 스크립트 디렉토리
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Python 경로
strPythonEXE = "Q:\Phtyon 3\python.exe"
strScript = objFSO.BuildPath(strScriptDir, "craigslist_auto_rpa.py")

' 로그인 셋업: Chrome 창 보이게 실행, cmd 창도 보이게 (1 = 일반)
' 사용자가 Chrome에서 이메일 링크 클릭 후 Enter 누르면 쿠키 저장됨
objShell.Run "cmd /k """ & strPythonEXE & """ -X utf8 """ & strScript & """ --login-setup --account default", 1, False
