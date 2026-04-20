' BRIDGE RPA 계정 선택 런처 (CMD창 없음)
' 아이콘 더블클릭 → 계정 선택창 → 선택 계정 순차 실행

Set objShell = CreateObject("WScript.Shell")
Set objFSO   = CreateObject("Scripting.FileSystemObject")

' ── 1단계: 좀비 Chrome/ChromeDriver 프로세스 정리 (메모리 확보) ──
' chromedriver.exe는 항상 RPA 전용이므로 안전하게 종료
objShell.Run "taskkill /F /IM chromedriver.exe", 0, True

' ── 2단계: 잠금 파일 정리 ──
strDir   = objFSO.GetParentFolderName(WScript.ScriptFullName)
strLock  = strDir & "\logs\.rpa_running.lock"
If objFSO.FileExists(strLock) Then
    On Error Resume Next
    objFSO.DeleteFile strLock, True
    On Error GoTo 0
End If

' ── 3단계: 런처 실행 ──
strPythonW = "Q:\Phtyon 3\pythonw.exe"
strScript  = objFSO.BuildPath(strDir, "rpa_select_launcher.py")

' 0 = 창 완전 숨김, False = 기다리지 않음 (런처 자체가 UI 담당)
objShell.Run """" & strPythonW & """ -X utf8 """ & strScript & """", 0, False
