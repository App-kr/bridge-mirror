' BRIDGE RPA 계정 선택 런처 (CMD창 없음)
' 2026-04-28 정책 변경:
'   - 살아있는 launcher 절대 죽이지 않음 (RPA 작업 중일 수 있음)
'   - launcher.py 의 single-instance 체크가 알아서 기존 창 복원
'   - 좀비 정리는 launcher.py 가 자체 처리 (visible 체크 후 kill)
'   - vbs 는 최소한의 검증만

Set objShell = CreateObject("WScript.Shell")
Set objFSO   = CreateObject("Scripting.FileSystemObject")

strDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' ── 1단계: 진입점 파일 검증 ──
strPythonW = "Q:\Phtyon 3\pythonw.exe"
strScript  = objFSO.BuildPath(strDir, "rpa_select_launcher.py")

If Not objFSO.FileExists(strPythonW) Then
    MsgBox "Python 경로 없음: " & strPythonW, 16, "BRIDGE RPA 오류"
    WScript.Quit 1
End If
If Not objFSO.FileExists(strScript) Then
    MsgBox "런처 스크립트 없음: " & strScript, 16, "BRIDGE RPA 오류"
    WScript.Quit 1
End If

' ── 2단계: 런처 실행 (single-instance 체크는 launcher.py 가 담당) ──
'   - 살아있는 launcher 가 있으면 → launcher.py 가 SW_RESTORE + BringToTop 후 sys.exit(0)
'   - 좀비 launcher 면 → launcher.py 가 visible 체크 → kill 후 새 인스턴스
'   - 클린 상태면 → 새 launcher 시작 + _ensure_visible_first 자동 화면 표시
' 0 = 창 완전 숨김, False = 기다리지 않음
objShell.Run """" & strPythonW & """ -X utf8 """ & strScript & """", 0, False
